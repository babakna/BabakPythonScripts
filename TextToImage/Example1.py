from diffusers import StableDiffusionPipeline
import torch

# Load the model
pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16,  # Use float16 for GPU efficiency
    use_safetensors=True
).to("cuda")  # Use "cpu" if no GPU

# Generate an image
prompt = "a futuristic city with flying cars, cyberpunk style, 4k"
image = pipe(prompt=prompt).images[0]

# Save the image
image.save("output.png")