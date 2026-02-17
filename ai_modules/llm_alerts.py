"""
LLM-Powered Smart Alert Generation for SmartCap AI
Generates natural, contextual voice alerts using AI
"""

import os
import json
import random
from typing import List, Dict, Optional

# Try to import LLM libraries
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class SmartAlertGenerator:
    """Generates natural language alerts using LLM or smart templates"""
    
    def __init__(self):
        self.llm_client = None
        self.llm_provider = None
        self._init_llm()
        
        # Context memory for smarter alerts
        self.last_objects = []
        self.last_alert_time = 0
        self.environment_context = "unknown"  # indoor/outdoor/street
        
    def _init_llm(self):
        """Initialize LLM client based on available API keys"""
        
        # Try Groq (fast, free tier)
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key and OPENAI_AVAILABLE:
            try:
                self.llm_client = OpenAI(
                    api_key=groq_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                self.llm_provider = "groq"
                print("LLM: Using Groq (llama-3.3-70b)")
                return
            except Exception as e:
                print(f"Groq init failed: {e}")
        
        # Try OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key and OPENAI_AVAILABLE:
            try:
                self.llm_client = OpenAI(api_key=openai_key)
                self.llm_provider = "openai"
                print("LLM: Using OpenAI GPT-4")
                return
            except Exception as e:
                print(f"OpenAI init failed: {e}")
        
        # Try Google Gemini
        gemini_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=gemini_key)
                self.llm_client = genai.GenerativeModel('gemini-1.5-flash')
                self.llm_provider = "gemini"
                print("LLM: Using Google Gemini")
                return
            except Exception as e:
                print(f"Gemini init failed: {e}")
        
        # Fallback to smart templates
        print("LLM: No API key found, using smart templates")
        self.llm_provider = "templates"
    
    def generate_alert(self, detections: List[Dict], location: str = None) -> str:
        """
        Generate a natural language alert for detected objects.
        
        Args:
            detections: List of detection dicts with class, distance, alert_level
            location: Optional current location name
            
        Returns:
            Natural language alert string
        """
        if not detections:
            return None
        
        # Sort by urgency
        critical = [d for d in detections if d.get('alert_level') == 'CRITICAL']
        warning = [d for d in detections if d.get('alert_level') == 'WARNING']
        
        if self.llm_provider in ["groq", "openai"]:
            return self._generate_with_openai_compatible(detections, critical, warning, location)
        elif self.llm_provider == "gemini":
            return self._generate_with_gemini(detections, critical, warning, location)
        else:
            return self._generate_with_templates(detections, critical, warning, location)
    
    def _generate_with_openai_compatible(self, detections, critical, warning, location) -> str:
        """Generate alert using OpenAI-compatible API (OpenAI, Groq)"""
        try:
            # Build context with movement info
            objects_desc = ", ".join([
                f"{d['class']} {d.get('movement_text', '')} at {d.get('distance', 'unknown distance')}"
                for d in detections[:5]
            ])
            
            urgency = "critical" if critical else "moderate" if warning else "low"
            
            # Check for approaching objects
            approaching_objects = [d for d in detections if d.get('movement', {}).get('approaching')]
            approaching = len(approaching_objects) > 0
            
            # Check for person approaching
            person_approaching = any(d['class'] == 'person' and d.get('movement', {}).get('approaching') for d in detections)
            
            # Check for vehicles
            vehicles_approaching = any(d['class'] in ['car', 'bicycle', 'motorcycle', 'bus', 'truck'] 
                                       and d.get('movement', {}).get('approaching') for d in detections)
            
            prompt = f"""You are a voice assistant for a blind person's navigation cap. Generate a brief, urgent spoken alert.

Detected objects: {objects_desc}
Urgency: {urgency}
{"PERSON APPROACHING - WARN IMMEDIATELY!" if person_approaching else ""}
{"VEHICLE APPROACHING - DANGER!" if vehicles_approaching else ""}
{"Object approaching!" if approaching and not person_approaching and not vehicles_approaching else ""}
{'Location: ' + location if location else ''}

Rules:
- Maximum 8-10 words for approaching alerts
- For person approaching: "Careful, someone coming toward you" or "Person approaching, X meters"
- For vehicle approaching: "Watch out! Vehicle coming" or "Danger, car approaching"
- For obstacles approaching: "Stop! Obstacle ahead" or "Careful, X getting closer"
- Be URGENT for approaching objects - this is safety critical
- Always mention distance
- Sound natural but firm

Generate ONLY the spoken alert text:"""

            model = "llama-3.3-70b-versatile" if self.llm_provider == "groq" else "gpt-4o-mini"
            
            response = self.llm_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.7
            )
            
            alert = response.choices[0].message.content.strip()
            # Clean up any quotes
            alert = alert.strip('"\'')
            return alert
            
        except Exception as e:
            print(f"LLM API error: {e}")
            return self._generate_with_templates(detections, critical, warning, location)
    
    def _generate_with_gemini(self, detections, critical, warning, location) -> str:
        """Generate alert using Google Gemini"""
        try:
            objects_desc = ", ".join([
                f"{d['class']} at {d.get('distance', 'unknown')}"
                for d in detections[:5]
            ])
            
            urgency = "CRITICAL" if critical else "WARNING" if warning else "INFO"
            
            prompt = f"""Generate a brief voice alert for a blind person. Max 12 words.
Objects: {objects_desc}
Urgency: {urgency}
Output only the spoken text:"""

            response = self.llm_client.generate_content(prompt)
            return response.text.strip().strip('"\'')
            
        except Exception as e:
            print(f"Gemini error: {e}")
            return self._generate_with_templates(detections, critical, warning, location)
    
    def _generate_with_templates(self, detections, critical, warning, location) -> str:
        """Generate alert using smart templates (no LLM needed)"""
        
        if critical:
            obj = critical[0]
            distance = obj.get('distance', 'very close')
            obj_name = obj.get('class', 'obstacle')
            movement_text = obj.get('movement_text', '')
            is_approaching = obj.get('movement', {}).get('approaching', False)
            
            if is_approaching:
                templates = [
                    f"Warning! {obj_name} approaching fast, {distance}",
                    f"Careful! {obj_name} getting closer, now {distance}",
                    f"Alert! {obj_name} coming toward you, {distance}",
                    f"Watch out! {obj_name} approaching, {distance} away"
                ]
            elif movement_text:
                templates = [
                    f"Careful! {obj_name} {movement_text}, {distance}",
                    f"Warning, {obj_name} {movement_text}, {distance}",
                    f"Watch out! {obj_name} {distance}, {movement_text}"
                ]
            else:
                templates = [
                    f"Careful! {obj_name} {distance} ahead",
                    f"Watch out, {obj_name} {distance}",
                    f"Stop! {obj_name} directly ahead, {distance}",
                    f"Warning, {obj_name} very close",
                    f"Heads up! {obj_name} {distance} in front"
                ]
            return random.choice(templates)
        
        elif warning:
            obj = warning[0]
            distance = obj.get('distance', 'nearby')
            obj_name = obj.get('class', 'object')
            movement_text = obj.get('movement_text', '')
            is_approaching = obj.get('movement', {}).get('approaching', False)
            
            # Add context for specific objects
            context_phrases = {
                'person': ['Someone', 'A person'],
                'car': ['Vehicle', 'A car'],
                'bicycle': ['Bicycle', 'A bike'],
                'dog': ['A dog', 'Dog'],
                'chair': ['Chair', 'A chair'],
            }
            
            name = random.choice(context_phrases.get(obj_name, [obj_name.capitalize()]))
            
            if is_approaching:
                templates = [
                    f"{name} approaching, now {distance}",
                    f"{obj_name} getting closer, {distance}",
                    f"{name} coming toward you, {distance}"
                ]
            elif movement_text:
                templates = [
                    f"{name} {movement_text}, {distance}",
                    f"{obj_name} {movement_text}, {distance} away",
                    f"{name} {distance}, {movement_text}"
                ]
            else:
                templates = [
                    f"{name} {distance} ahead",
                    f"{obj_name} detected, {distance}",
                    f"There's a {obj_name} {distance} away",
                    f"{name} detected {distance} ahead"
                ]
            return random.choice(templates)
        
        else:
            # Safe object, just inform
            obj = detections[0] if detections else None
            if obj:
                movement_text = obj.get('movement_text', '')
                if movement_text:
                    return f"{obj.get('class', 'object')} {movement_text}, {obj.get('distance', 'ahead')}"
                return f"{obj.get('class', 'object')} in view, {obj.get('distance', 'ahead')}"
            return None


# Singleton
_alert_generator = None

def get_alert_generator() -> SmartAlertGenerator:
    global _alert_generator
    if _alert_generator is None:
        _alert_generator = SmartAlertGenerator()
    return _alert_generator
