terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

data "aws_ami" "al2024" {
  filter {
    name   = "image-id"
    values = ["ami-0866a04d72a1f5479"]
  }

  owners = ["137112412989"] # amazon
}

data "aws_ec2_instance_type" "al2024" {
  instance_type = "t2.micro"
}
