# lora-workflow

## About this project

This project contains a number of tools that are intended to be used together (in a workflow) to help take a number of
source images and eventually produce a LoRA for use with a Stable Diffusion model.

### Setting up the local repo

- Clone this repo from GitHub
- Add **kohya-ss/sd-scripts** as a submodule:

```bash
cd run-training
git submodule add https://github.com/bmaltais/kohya_ss.git
```

- Install **uv** and run `uv venv` to create a virtual environment.
- Run `uv sync` to install the dependencies from **pyproject.toml**.

## High level workflow

This workflow uses **Adobe Lightroom** as the library in which the source images will be collected, tagged and filtered.

Once the images are exported they are processed using **Python scripts** that will (1) resize (shrink) the images to the
correct dimensions for SD training and (2) extract the Adobe keywords (tags) and create caption files for each image.

Finally, the **kohya-ss/sd-scripts** will be used to perform the actual training.

## Semi-detailed workflow

### Project name

In the workflow below the "project name" will be used to name the subject of the LoRA that you are training. This should
be a unique term that will be used when generating images to invoke the subject of the LoRA.

### 1. Add images to Adobe Lightroom

- Gather the source images for the LoRA and import them into Adobe Lightroom.
- Organize these into folder(s) so they can be worked on without being confused with other LoRA projects.
- Crop images into either 1x1 or 2x3 aspect ratios. Sorting the images by aspect ratio should help with this.
- Apply star ratings based on image resolution and quality. Sorting the images by pixel dimensions can help.
For example: five-stars for the best quality images to two-stars for those that aren't large enough (e.g. less than 512
pixels on the shortest side). Delete images that are worse than this.

### 2. Tag images

- Add keywords to the images that will be used to tag/caption the images for training.

#### Keywords NOT to add

- Avoid adding keywords to the images for features that are intrinsic to your subject.

#### Keywords NOT to export

Some keywords are useful to help organize and filter your images, but might not be needed when tagging/captioning the
dataset. For example:

- Don't include the actual word(s) for the subject of the LoRA you are creating; this will be included later when you
caption the images.

### 3. Output images

- Create a **Publish Service** to output the images to disk:
  - **Type:** Hard drive export
  - **Name/Description:** Training datasets
  - **Export Location:** A path to a folder under which the training will be run
  - **File Naming:** Custom setting: `{Folder Name}-{Filename}`
  - **Image Format:** PNG
  - **Resize to fit:** No
  - **Sharpen for:** Screen (standard)
  - **Metadata:** All metadata, keep location info & use Lightroom hierarchy.
  - **Watermarking:** No
- Create a **Published Collection Set**
  - Name this according to the project; this creates a top-level folder for the dataset, named for this project.
  - Create **Smart Collections** within this Collection Set; each one of these will be a folder within the project
folder. Remember that by putting a numerical prefix on the folder name, e.g. "5_\<something\>", will determine how much
relative emphasis is put on the images in that folder when it comes to training.

### 4. Resize images

- Navigate to the **prep-dataset** folder in this repo.
- Run the **resize_iamge.py** script to resize images to ensure that their smallest dimension is appropriate for the
model, e.g. 512 pixels for SD 1.5 models.

```bash
uv run ./resize_images.py --help
```

### 5. Caption the images

- Run the **caption_iamge.py** script to build sensible captions for each images based on the keywords (tags) exported
from Adobe Lightroom.

```bash
uv run ./caption_images.py --help
```

### 6. Run training
