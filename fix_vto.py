# Read the file
with open('vto_system.py', 'r') as f:
    content = f.read()

# Find and replace the generate_base_model method to add better error handling
old_code = '''        # Extract image from response
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'inline_data'):
                    mime_type = part.inline_data.mime_type
                    data = base64.b64encode(part.inline_data.data).decode('utf-8')
                    return f"data:{mime_type};base64,{data}"
        
        # Fallback: try candidates
        if hasattr(response, 'candidates'):
            for candidate in response.candidates:
                if hasattr(candidate, 'content'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data'):
                            mime_type = part.inline_data.mime_type
                            data = base64.b64encode(part.inline_data.data).decode('utf-8')
                            return f"data:{mime_type};base64,{data}"
        
        raise ValueError("Failed to generate base model image")'''

new_code = '''        # Check for blocking first
        if hasattr(response, 'prompt_feedback'):
            feedback = response.prompt_feedback
            if hasattr(feedback, 'block_reason'):
                raise ValueError(f"Request blocked: {feedback.block_reason}")
        
        # Check candidates exist
        if not hasattr(response, 'candidates') or not response.candidates:
            raise ValueError("No candidates returned. Image might have been blocked by safety filters.")
        
        # Extract image from candidates
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data'):
                        mime_type = part.inline_data.mime_type
                        data = base64.b64encode(part.inline_data.data).decode('utf-8')
                        return f"data:{mime_type};base64,{data}"
        
        raise ValueError("Failed to generate base model image - no image data in response")'''

content = content.replace(old_code, new_code)

with open('vto_system.py', 'w') as f:
    f.write(content)

print("✅ Fixed error handling")
