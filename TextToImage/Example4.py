from diffusers import StableDiffusionPipeline
import torch

# Load model
model_id = "CompVis/stable-diffusion-v1-4"  # Example free model
pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
pipe = pipe.to("cuda")  # Move to GPU if available

# Generate image
prompt = "a photo of a cat sitting on a rainbow"
image = pipe(prompt).images[0]
image.save("generated_image.png")