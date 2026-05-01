# Instructions for Agentic AI Tools

## Your role

Your role is to support the User developing a simple scaffold around the process of creating Loras for Stable Diffusion.
This will involve developing and/or using different tools including:

- Preparing a dataset of images for training
- Running Lora training
- Testing the quality of the output

You will also support the user designing and documenting this process.

### Preparation work by the user

The user will have curated a set of images to use for the Lora training, and the "type" of Lora they want to create, for
example an artistic style, a character/person likeness, etc.

The user will have used Adobe Lightroom to create a library of these images and then to export them to a folder on disk.
You need to ensure that the output of this export is suitable for the training process.

### Understanding kohya_ss tools

You need to understand the "kohya_ss" tools and support the user who may be unfamiliar with these git projects. There
are two repos included as submodules in this project:

- [kohya-ss/sd-scripts](https://github.com/kohya-ss/sd-scripts)
- [bmaltais/kohya_ss (GUI)](https://github.com/bmaltais/kohya_ss.git)

The GUI project for kohya_ss scripts is provided for reference; it is expected that THIS project will call the
**sd-scripts** directly with pre-configured settings.

## About this project

@README.md
