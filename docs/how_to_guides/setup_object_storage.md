# Setup Object Storage For Syncing Files

In this guide you will learn how to setup access to an AWS S3 API compliant object store service. Once this access has been setup, you will be able to sync files with the Beatcloud.

## Why sync files in the first place?
There are two primary reasons to sync your files to the cloud:

1. Creating a reliable backup for your files
1. Enabling remote sharing of your collection with other DJs

## How it's done

1. It should be the case that `awscli` was installed alongside DJ Tools; check that it works by running `aws`
    - In the event that you cannot run the `aws` command, you'll have to install it manually:
        - Mac installation: `brew install awscli`
        - Linux installation: `sudo apt-get install awscli`
        - Windows installation [[official instructions](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html)]: [download installer](https://awscli.amazonaws.com/AWSCLIV2.msi) OR run:
&nbsp;&nbsp;&nbsp;`msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi`

1. [Create and setup an account for AWS S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html) (you could use any AWS S3 API compliant cloud storage solution, e.g. [MinIO](https://min.io/), but I've not tested anything else)
1. At the time of writing, it's required that your bucket has the address `dj.beatcloud.com`
1. Setup a profile (so as to not conflict with pre-existing or future profiles) for your keys:

    &nbsp;&nbsp;&nbsp;`aws configure --profile DJ`

1. Enter the `access_key` and `secret_key` (default values for the rest of the configuration is fine)
1. Set the configuration option `AWS_PROFILE` in `config.yaml` to match this profile name
