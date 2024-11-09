# Define the provider
provider "aws" {
  region = "eu-north-1"
}


# Create a VPC
resource "aws_vpc" "default" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "Django_EC2_VPC"
  }
}

# Create an Internet Gateway
resource "aws_internet_gateway" "default" {
  vpc_id = aws_vpc.default.id
  tags = {
    Name = "Django_EC2_Internet_Gateway"
  }
}

# Create a Route Table
resource "aws_route_table" "default" {
  vpc_id = aws_vpc.default.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.default.id
  }
  tags = {
    Name = "Django_EC2_Route_Table"
  }
}

# Create two subnets
resource "aws_subnet" "subnet1" {
  vpc_id                  = aws_vpc.default.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "eu-north-1a"
  tags = {
    Name = "Django_EC2_Subnet_1"
  }
}

resource "aws_subnet" "subnet2" {
  vpc_id                  = aws_vpc.default.id
  cidr_block              = "10.0.2.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "eu-north-1b"
  tags = {
    Name = "Django_EC2_Subnet_2"
  }
}

# Associate route table with subnets
resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.subnet1.id
  route_table_id = aws_route_table.default.id
}

resource "aws_route_table_association" "b" {
  subnet_id      = aws_subnet.subnet2.id
  route_table_id = aws_route_table.default.id
}

# Create a security group
resource "aws_security_group" "ec2_sg" {
  vpc_id = aws_vpc.default.id

  ingress {
    from_port = 80
    to_port   = 80
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 8000
    to_port   = 8000
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 5173
    to_port   = 5173
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "EC2_Security_Group"
  }
}


# Define variables for the secret key and SSH key pair name
variable "secret_key" {
  description = "The Secret Key for Django"
  type        = string
  sensitive   = true
}

variable "DEBUG" {
  description = "Debug value"
  type        = string
}

variable "POSTGRES_DB" {
  description = "DB name"
  type        = string
}

variable "POSTGRES_USER" {
  description = "DB user"
  type        = string
}

variable "POSTGRES_PASSWORD" {
  description = "DB password"
  type        = string
}

variable "USE_POSTGRES" {
  description = "DB password"
  type        = string
}

variable "VITE_PROXY_URL" {
  description = "vite proxy url"
  type        = string
}

variable "VITE_HOST" {
  description = "host vite server"
  type        = number
}

locals {
  DATABASE_URL = "postgres://${var.POSTGRES_USER}:${var.POSTGRES_PASSWORD}@db:5432/${var.POSTGRES_DB}"
}

data "template_file" "env_file" {
  template = <<-EOT
    DEBUG=${var.DEBUG}
    USE_POSTGRES=${var.USE_POSTGRES}
    POSTGRES_DB=${var.POSTGRES_DB}
    POSTGRES_USER=${var.POSTGRES_USER}
    POSTGRES_PASSWORD=${var.POSTGRES_PASSWORD}
    DATABASE_URL=${local.DATABASE_URL}
    VITE_PROXY_URL=${var.VITE_PROXY_URL}
    VITE_HOST=${var.VITE_HOST}
    SECRET_KEY=${var.secret_key}
  EOT
}

# IAM role for EC2 to access ECR
resource "aws_iam_role" "ec2_role" {
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Principal = {
        Service = "ec2.amazonaws.com",
      },
      Effect = "Allow",
    }],
  })
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "django_ec2_complete_profile"
  role = aws_iam_role.ec2_role.name
}

# Launch an EC2 instance
resource "aws_instance" "web" {
  ami                    = "ami-04b54ebf295fe01d7"
  instance_type          = "t3.micro"
  key_name               = "terraform-ssh"
  subnet_id              = aws_subnet.subnet1.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  associate_public_ip_address = false
  user_data_replace_on_change = true

  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  user_data = <<-EOF
    #!/bin/bash
    set -ex
    yum update -y
    yum install -y yum-utils

    # Install Docker
    yum install -y docker
    service docker start

    # Install AWS CLI
    yum install -y aws-cli

    # Install Docker Compose
    curl -SL https://github.com/docker/compose/releases/download/v2.30.3/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    # Authenticate to ECR
    docker login -u AWS -p $(aws ecr get-login-password --region eu-north-1) 762233752592.dkr.ecr.eu-north-1.amazonaws.com/evsite

    # Pull the Docker image from ECR
    docker pull 762233752592.dkr.ecr.eu-north-1.amazonaws.com/evsite:frontend
    docker pull 762233752592.dkr.ecr.eu-north-1.amazonaws.com/evsite:backend
    docker pull postgres:15

    # Create the .env file
    echo '${data.template_file.env_file.rendered}' > /home/ec2-user/.env

    # Set up Docker Compose
    cd /home/ec2-user
    # Copy the docker-compose.yml file to the instance
    echo
    'services:
      db:
        image: postgres:15
        shm_size: 1gb
        restart: on-failure:5
        env_file: .env
        ports:
          - 5432:5432
        volumes:
          - db_data:/var/lib/postgresql/data
          - db_logs:/var/log/postgresql
        healthcheck:
          test: [ "CMD-SHELL", "pg_isready -U league" ]
          interval: 10s
          timeout: 5s
          retries: 5

      backend:
        image: 762233752592.dkr.ecr.eu-north-1.amazonaws.com/evsite:backend
        restart: on-failure:5
        command: bash -c "python manage.py migrate && gunicorn evsite.wsgi:application --bind 0.0.0.0:8000"
        env_file: .env
        ports:
          - 8000:8000
        depends_on:
          db:
            condition: service_healthy

      frontend:
        image: 762233752592.dkr.ecr.eu-north-1.amazonaws.com/evsite:frontend
        restart: on-failure:5
        env_file: .env
        command: bash -c "npm install && npm run dev"
        volumes:
          - type: bind
            source: ./frontend
            target: /code
        ports:
          - 5173:5173
        depends_on:
          backend:
            condition: service_started

    volumes:
      db_data:
      db_logs:' > docker-compose.yml

    # Start Docker Compose
    docker-compose --env-file .env up -d
  EOF

  tags = {
    Name = "Django_EC2_evsite"
  }
}

resource "aws_eip_association" "eip_assoc" {
  instance_id = aws_instance.web.id
  allocation_id = "eipalloc-024ee5656548aa974"
}

output "ec2_public_ip" {
  value = aws_instance.web.public_ip
}