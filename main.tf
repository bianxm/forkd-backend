terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.16"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = ">= 2.19.2"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

resource "aws_instance" "forkd_server" {
  ami           = "ami-0a695f0d95cefc163"
  instance_type = "t2.micro"

  tags = {
    Name = "My Web Server"
  }
}

resource "aws_security_group" "instance_sg" {
  description = "launch-wizard-2 created 2023-05-08T21:20:48.411Z"
}

resource "aws_vpc_security_group_ingress_rule" "http_into_instance" {
  description       = "http from internet"
  security_group_id = aws_security_group.http_into_instance.id
  ip_protocol       = "tcp"
  referenced_security_group_id = aws_security_group.lb_sg.id
  from_port         = 80
  to_port           = 80
}

# review health check settings and stickiness settings
# these are just the defaults
# maybe rename as well
resource "aws_lb_target_group" "my_target_group" {
  port     = 80
  protocol = "HTTP"
  tags     = {}
  vpc_id   = var.vpc_id
  health_check {
    enabled             = true
    healthy_threshold   = 5
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  stickiness {
    cookie_duration = 86400
    enabled         = false
    type            = "lb_cookie"
  }
}

# not able to import this, so i just re-made it
resource "aws_lb_target_group_attachment" "forkd_server" {
  target_group_arn = aws_lb_target_group.my_target_group.arn
  target_id        = aws_instance.forkd_server.id
}

resource "aws_lb" "forkd_lb" {
  load_balancer_type = "application"
  security_groups = [aws_security_group.lb_sg.id]
}

resource "aws_security_group" "lb_sg" {
  description = "launch-wizard-3 created 2023-08-23T14:40:56.487Z"
}

resource "aws_vpc_security_group_ingress_rule" "lb_sg_http" {
  description       = "http from internet"
  security_group_id = aws_security_group.lb_sg.id
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_ingress_rule" "lb_sg_https" {
  description       = "https from internet"
  security_group_id = aws_security_group.lb_sg.id
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
}

resource "aws_lb_listener" "http_into_lb" {
  load_balancer_arn = aws_lb.forkd_lb.arn 
  port = 80
  protocol = "HTTP"
  default_action {
    redirect {
      port = "443" 
      protocol = "HTTPS"
      status_code = "HTTP_301"
    }
    type = "redirect"
  }
}

resource "aws_lb_listener" "https_into_lb" {
  load_balancer_arn = aws_lb.forkd_lb.arn 
  certificate_arn = var.cert_arn
  port = 443
  protocol = "HTTPS"
  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.my_target_group.arn
  }
}

resource "cloudflare_record" "forkd_cname" {
  zone_id = var.zone_id
  type    = "CNAME"
  name    = "forkd"
  value   = lower(aws_lb.forkd_lb.dns_name)

  proxied = false
}
