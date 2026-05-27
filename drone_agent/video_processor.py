import os
import cv2
import base64
from PIL import Image
import io
import google.generativeai as genai
from openai import OpenAI

# Pre-baked security narrative matched with simulated telemetry checkpoints
SIMULATED_VISUAL_LOGS = [
    {
        "frame_index": 0,
        "location": "Drone Docking Station",
        "description": "Patrol mission initiated. Drone taking off from Docking Station. System diagnostics indicate all systems nominal, battery at 100%. Clear night sky, wind 4 knots.",
        "tags": ["takeoff", "dock", "nominal"]
    },
    {
        "frame_index": 1,
        "location": "Main Entrance Gate",
        "description": "Arrived at Main Entrance Gate. Front gates are locked and secure. No vehicles are visible in the immediate vicinity. Lighting is functional.",
        "tags": ["gate", "secure", "locked"]
    },
    {
        "frame_index": 2,
        "location": "Visitor Parking Lot",
        "description": "Hovering over Visitor Parking Lot. A grey sedan is parked in a dark, non-designated area near the perimeter trees. Headlights are off, vehicle appears unoccupied.",
        "tags": ["vehicle", "sedan", "parking-lot", "suspicious"]
    },
    {
        "frame_index": 3,
        "location": "Office HQ Perimeter",
        "description": "Scanning Office HQ Perimeter. Thermal and optical cameras show lobby lights are off. However, a person wearing a dark hoodie is seen walking closely along the rear glass window. Person appears to be looking inside with a flashlight.",
        "tags": ["person", "loitering", "hq", "suspicious", "flashlight"]
    },
    {
        "frame_index": 4,
        "location": "Warehouse Loading Docks",
        "description": "Overflying Warehouse Loading Docks. A blue Ford F150 pickup truck is parked near Dock 3. A second individual is seen unloading dark plastic crates from the back of the truck near the warehouse roll-up door.",
        "tags": ["vehicle", "truck", "ford-f150", "person", "unloading", "loading-dock", "intrusion"]
    },
    {
        "frame_index": 5,
        "location": "South Fenced Boundary",
        "description": "Monitoring South Fenced Boundary. The chain-link security fence is in good structural condition. No foreign objects, scaling gear, or breaches detected. Area is quiet.",
        "tags": ["fence", "secure", "quiet"]
    },
    {
        "frame_index": 6,
        "location": "Hazardous Waste Zone",
        "description": "Flying over the Hazardous Waste Storage Area. Thermal cameras detect no heat anomalies. However, optical feed shows one yellow metal drum has tipped over on its side. Possible chemical container breach.",
        "tags": ["chemical", "drum", "tipped-over", "leak", "safety-hazard"]
    },
    {
        "frame_index": 7,
        "location": "Drone Docking Station",
        "description": "Patrol complete. Returning to Drone Docking Station. Descending, aligning with docking guide rails. Landing successful. Battery level low, starting recharge sequence.",
        "tags": ["landing", "dock", "charging", "complete"]
    }
]

class VideoProcessor:
    def __init__(self, mode="simulated"):
        self.mode = mode.lower()
        self.current_sim_index = 0
        
        # Initialize API clients if keys are present
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if self.mode == "live":
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                print("VideoProcessor initialized in LIVE Mode using Gemini API.")
            elif self.openai_api_key:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print("VideoProcessor initialized in LIVE Mode using OpenAI API.")
            else:
                print("WARNING: Live mode requested but no API keys found. Defaulting to Simulated Mode.")
                self.mode = "simulated"

    def get_simulated_frame(self, telemetry_location):
        """Returns a matched simulated description based on drone location."""
        # Find a log that closely matches the current location
        matched_log = None
        for log in SIMULATED_VISUAL_LOGS:
            if log["location"].lower() in telemetry_location.lower():
                matched_log = log
                break
                
        if not matched_log:
            # Fallback
            matched_log = SIMULATED_VISUAL_LOGS[self.current_sim_index]
            self.current_sim_index = (self.current_sim_index + 1) % len(SIMULATED_VISUAL_LOGS)
            
        return {
            "frame_index": matched_log["frame_index"],
            "description": matched_log["description"],
            "tags": matched_log["tags"]
        }

    def process_frame(self, frame_img, frame_index, location_name):
        """Processes an actual image frame using the configured VLM API."""
        if self.mode == "simulated" or not (self.gemini_api_key or self.openai_api_key):
            return self.get_simulated_frame(location_name)
            
        # Convert OpenCV image (BGR) to PIL Image (RGB) for model ingestion
        rgb_img = cv2.cvtColor(frame_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        
        prompt = (
            f"You are a Drone Security Analyst Agent monitoring a commercial property. "
            f"This frame was captured near the '{location_name}'. "
            f"Analyze the image for security breaches, safety hazards, vehicles, people, "
            f"or properties. Provide a 2-3 sentence, highly detailed, matter-of-fact report. "
            f"Also, output 3-5 tags of key entities or states found in the image (e.g. ['vehicle', 'person', 'secure', 'loitering'])."
            f"Return your response strictly in the following JSON format:\n"
            f'{{"description": "your description here", "tags": ["tag1", "tag2", "tag3"]}}'
        )
        
        try:
            if self.gemini_api_key:
                # Call Gemini
                response = self.gemini_model.generate_content([pil_img, prompt])
                text = response.text.strip()
                # Simple extraction of JSON content from markdown block if needed
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                import json
                result = json.loads(text)
                return {
                    "frame_index": frame_index,
                    "description": result.get("description", "Image analyzed with no anomalies found."),
                    "tags": result.get("tags", ["patrol"])
                }
                
            elif self.openai_api_key:
                # Call OpenAI GPT-4o
                buffered = io.BytesIO()
                pil_img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                            ]
                        }
                    ],
                    max_tokens=300
                )
                
                import json
                result = json.loads(response.choices[0].message.content)
                return {
                    "frame_index": frame_index,
                    "description": result.get("description", "Image analyzed with no anomalies found."),
                    "tags": result.get("tags", ["patrol"])
                }
                
        except Exception as e:
            print(f"VLM API Error: {e}. Falling back to simulated metadata.")
            return self.get_simulated_frame(location_name)
            
    def process_video_file(self, video_path, sample_rate_frames=30, location_sequence=None):
        """Reads a video file and processes frames at a set sample rate."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at {video_path}")
            
        cap = cv2.VideoCapture(video_path)
        frames_data = []
        frame_idx = 0
        saved_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % sample_rate_frames == 0:
                # Map standard locations if a sequence is not provided
                loc = "Patrol Area"
                if location_sequence and saved_idx < len(location_sequence):
                    loc = location_sequence[saved_idx]
                    
                processed = self.process_frame(frame, saved_idx, loc)
                frames_data.append(processed)
                saved_idx += 1
                
            frame_idx += 1
            
        cap.release()
        return frames_data
