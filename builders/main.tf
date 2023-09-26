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

data "aws_ami" "al2023" {
  filter {
    name   = "image-id"
    values = ["ami-06f621d90fa29f6d0"]
  }

  owners = ["137112412989"] # amazon
}

data "aws_ec2_instance_type" "al2023" {
  instance_type = "t2.micro"
}

resource "aws_instance" "server1" {
  ami           = data.aws_ami.al2023.id
  instance_type = data.aws_ec2_instance_type.al2023.instance_type
}

resource "aws_ec2_instance_state" "server1_state" {
  instance_id = aws_instance.server1
  state       = "stopped"
}
