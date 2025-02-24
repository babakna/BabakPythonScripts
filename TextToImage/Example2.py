from diffusers import KandinskyPipeline, KandinskyPriorPipeline
import torch

# Load prior (text embedding) and decoder (image generation)
prior_pipe = KandinskyPriorPipeline.from_pretrained(
    "kandinsky-community/kandinsky-2-2-prior",
    torch_dtype=torch.float16
).to("cuda")

decoder_pipe = KandinskyPipeline.from_pretrained(
    "kandinsky-community/kandinsky-2-2-decoder",
    torch_dtype=torch.float16
).to("cuda")

# Generate image embeddings
prompt = "a serene mountain landscape at sunset, oil painting"
image_embeds, negative_embeds = prior_pipe(prompt=prompt).to_tuple()

# Generate image
image = decoder_pipe(
    image_embeds=image_embeds,
    negative_image_embeds=negative_embeds,
    height=768,
    width=768,
).images[0]
image.save("kandinsky_output.png")