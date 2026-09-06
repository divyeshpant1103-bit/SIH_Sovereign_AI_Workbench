#First offline test testing the Warm Generation

Machine: GTX 1650 4GB laptop, Windows
Model: workbench (qwen2.5:3b-instruct-q4_K_M, num_ctx 8192)

Cold load:              24.9 s
Warm generation:        59.45 tokens/s
Warm prompt processing: 321.91 tokens/s
Warm total (94 tok):    1.7 s
Network state:          airplane mode, full offline

#For avoiding the cold start of 20s, one token request on startup

ollama run workbench "hi"

