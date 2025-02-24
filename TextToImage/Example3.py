from transformers import pipeline

# Load the pipeline
pipe = pipeline("text-to-image", model="dalle-mini/dalle-mini")

# Generate
image = pipe("a cute corgi wearing a superhero cape, digital art")[0]["image"]
image.save("dalle_mini_output.png")