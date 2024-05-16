from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from . models import CarEntry
import cv2
import numpy as np
import pytesseract
import re
import base64
from datetime import datetime
from django.utils import timezone
import pytz
from ipdb import set_trace

TIMEZONE = pytz.timezone('Asia/Kolkata')

IST = pytz.timezone('Asia/Kolkata')

@require_http_methods(["POST"])
@csrf_exempt
def detect(request):
    try:
        if 'image' in request.FILES:
            mode = request.POST.get('Mode')
            image_file = request.FILES['image']

            image = cv2.imdecode(np.frombuffer(image_file.read(), np.uint8), cv2.IMREAD_COLOR)
            
            # Convert the image to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Perform edge detection using Canny
            edges = cv2.Canny(blur, 50, 150)
            
            # Find contours in the edge-detected image
            contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours to find rectangular shapes
            rectangles = []
            for contour in contours:
                perimeter = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
                if len(approx) == 4 and cv2.contourArea(contour) > 1000: # Filter by number of corners and area
                    rectangles.append(contour)
            
            # Find the largest rectangle
            largest_rectangle = None
            largest_area = 0
            for contour in rectangles:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                if area > largest_area:
                    largest_area = area
                    largest_rectangle = (x, y, w, h)
            
            if largest_rectangle is not None:
                x, y, w, h = largest_rectangle
                roi = gray[y:y+h, x:x+w] # Region of interest
                plate_text = pytesseract.image_to_string(roi, config='--psm 6') # Perform OCR
                # Filter out special characters
                plate_text_filtered = re.sub(r'[^a-zA-Z0-9]', '', plate_text)
                # Draw the recognized text on top of the bounding box
                cv2.putText(image, plate_text_filtered, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)
                
                _, jpeg_image = cv2.imencode('.jpg', image)
                base64_image = base64.b64encode(jpeg_image.tobytes()).decode('utf-8')

                if mode == "Entry":
                    # Generate entry date and time
                    entry_date = datetime.now().strftime('%Y-%m-%d')
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    CarEntry.objects.create(license_plate = plate_text_filtered, entry_time = timezone.localtime())
                    return JsonResponse({
                        'image': base64_image,
                        'license_plate_no': plate_text_filtered,
                        'entry_date': entry_date,
                        'entry_time': entry_time
                    })
                elif mode == "Exit":
                        exit_date = datetime.now().strftime('%Y-%m-%d')
                        exit_time = datetime.now().strftime('%H:%M:%S')
                        carObject = CarEntry.objects.filter(license_plate = plate_text_filtered).latest('entry_time')
                        carEntry = carObject.entry_time.astimezone(IST)
                        difference = timezone.localtime() - carEntry

                        # Calculting Time in Minutes
                        total_seconds = difference.total_seconds()
                        print(f"tot sec",total_seconds)
                        # Calculate days after removing months
                        days = int(total_seconds // (24 * 60 * 60))
                        print(f"days",days)
                        # Calculate hours after removing months and days
                        hours = int((total_seconds % (24 * 60 * 60)) // (60 * 60))
                        print(f"hours",hours)
                        # Calculate minutes after removing months, days, and hours
                        minutes = int((total_seconds % (60 * 60)) // 60)
                        print(f"minutes",minutes)
                        bill=0

                        # Charge for days
                        bill += days * 200

                        # Charge for hours (excluding full days)
                        bill += hours * 10

                        bill+=50
                        
                        # set_trace()
                        # bill = (difference_minutes // 60) * 50
                        print(f"bill: ",bill)

                        return JsonResponse({
                        'image': base64_image,
                        'license_plate_no': plate_text_filtered,
                        'exit_date': exit_date,
                        'exit_time': exit_time,
                        'days': days,
                        'hours': hours,
                        'minutes': minutes,
                        'bill':bill,
                    })
            else:
                return JsonResponse({'error': 'No license plate detected in the image'}, status=400)
        else:
            return JsonResponse({'error': 'No image file provided in the request'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
