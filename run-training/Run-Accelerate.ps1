<#
.SYNOPSIS
    Calls `accelerate launch` from kohya-ss's sd_scripts repo.
#>
param (
    [Parameter(Mandatory)]
    [string]
    $ProjectName
)

if ($env:VIRTUAL_ENV -notmatch "kohya_ss"){
    Write-Error "Please enable the virtual environment in the kohya_ss folder."
    exit 1
}

if ((python --version) -notmatch "3.11"){
    Write-Error "Please use Python 3.11."
    exit 1
}

################################################################################
# Config:
# Full path to model you want to train FROM, or base model:
$ckpt = "S:/GenAI/ImageGen/data/models_sd1x/Checkpoints/realisticVisionV51_v51VAE.safetensors"
# Data set folder
$image_dir = "P:/Data/Training/$ProjectName"
# Output folder for your baked LORAs.
$output = "P:/Data/Training/_output/$ProjectName"
# Only use these for dreambooth style training. Point to an empty folder otherwise.
$reg_dir = "P:/Data/Training/_regularization"

################################################################################
# Training parameters

$train_batch_size           = 1        # Amount of images to process at once. I have 8GB of VRAM so I left it at 1, it just worked. Raise if you got more VRAM.
$learning_rate              = 0.0001   # Unet learning rate.
$text_encoder_learning_rate = 0.00005  # Text Encoder learning rate. This is the recommended value.
$num_epochs                 = 8        # Total number of epochs (amount of times the entire set is repeated)
$save_every_n_epochs        = 1        # Save checkpoints every X epochs.
$resolution                 = 512      # Resolution to work at. Higher requires more training for the unet and more VRAM.
$network_dim                = 128      # AKA Rank. Higher for more resemblance to the training images and bigger file size. 96-192 for characters. 160 was good for me.
$network_alpha              = 128      # Must be equal or lower than network dim. Dampens learning the lower it is, but avoids rounding issues.
$noise_offset               = 0.0      # Increases dynamic range of outputs. Every 0.1 dampens learning quite a bit, do more steps or higher training rates to compensate.
$clip_skip                  = 1        # Set it to 2 if you train from NAI.
$optimizer                  = "AdamW8bit"  # Valid values: "AdamW", "AdamW8bit", "Lion", "SGDNesterov", "SDGNesterov8bit", "DAdaptation", "AdaFactor"
# Default AdamW8bit (old --use_8bit_adam). DAdaptation requires setting learning rates to values between 0.1 and 1.0 as it tweaks them during training.
$scheduler                  = "cosine_with_restarts"

################################################################################
# Run training

$learning_rate = $learning_rate * $train_batch_size  # Seems to work better for the Unet.

Set-Location .\kohya-ss\sd-scripts

accelerate launch --num_cpu_threads_per_process 8 train_network.py `
    --network_module="networks.lora" `
    --pretrained_model_name_or_path=$ckpt --train_data_dir=$image_dir --reg_data_dir=$reg_dir --output_dir=$output `
    --caption_extension=".txt" --shuffle_caption --keep_tokens=1 `
    --prior_loss_weight=1 `
    --resolution="$resolution" `
    --enable_bucket --min_bucket_reso=320 --max_bucket_reso=960 `
    --train_batch_size="$train_batch_size" `
    --learning_rate="$learning_rate" --unet_lr="$learning_rate" --text_encoder_lr=$text_encoder_learning_rate `
    --max_train_epochs=$num_epochs `
    --mixed_precision="fp16" --save_precision="fp16" `
    --optimizer_type="$optimizer" --xformers `
    --save_every_n_epochs="$save_every_n_epochs" `
    --save_model_as=safetensors `
    --clip_skip="$clip_skip" `
    --seed=420 `
    --flip_aug `
    --network_dim="$network_dim" --network_alpha="$network_alpha" `
    --max_token_length=225 `
    --cache_latents `
    --lr_scheduler="$scheduler" `
    --noise_offset="$noise_offset"

Set-Location ..\..