Deployment Guide
================

This guide covers deployment strategies for the Lineup API.

.. note::
   Full deployment setup will be implemented in Phase 4 of development.
   This documentation will be updated as deployment infrastructure is built.

Overview
--------

The Lineup API is designed to be deployed on AWS with the following goals:

* **Cost Optimization** - Minimize cloud costs for low-traffic initial deployment
* **Scalability** - Design for future growth as user base expands
* **Security** - Follow AWS security best practices
* **Automation** - Fully automated CI/CD pipeline

Target Architecture
-------------------

Planned AWS Services
^^^^^^^^^^^^^^^^^^^^

* **Compute**: AWS Lambda (serverless) or ECS Fargate
* **Database**: Amazon RDS for PostgreSQL
* **Storage**: Amazon S3 (for PDF exports and static files)
* **API Gateway**: AWS API Gateway or Application Load Balancer
* **CI/CD**: GitHub Actions with AWS deployment
* **Secrets**: AWS Secrets Manager
* **Monitoring**: Amazon CloudWatch
* **DNS**: Amazon Route 53

Infrastructure as Code
^^^^^^^^^^^^^^^^^^^^^^

Infrastructure will be managed using **Pulumi** for:

* Reproducible infrastructure
* Version-controlled infrastructure changes
* Easy environment replication (dev, staging, production)
* Infrastructure testing

Cost Management
---------------

.. warning::
   Cost management and budget protection are critical priorities!

Planned Cost Protection Measures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. **AWS Budgets** with automatic actions
   
   * Set monthly budget limits
   * Automatic notifications at 50%, 80%, 100% thresholds
   * Automatic resource shutdown when budget exceeded

2. **Cost Anomaly Detection**
   
   * Detect unusual spending patterns
   * Immediate alerts for cost spikes

3. **Resource Tagging Strategy**
   
   * Tag all resources for cost tracking
   * Enable automated cost allocation

4. **Automatic Shutdowns**
   
   * Lambda functions to stop/terminate resources on budget breach
   * EventBridge rules for off-hours shutdown (if applicable)
   * Emergency shutdown procedures documented

5. **Regular Cost Reviews**
   
   * Weekly cost monitoring in development
   * Monthly cost optimization reviews

Cost Optimization Strategies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Use serverless (Lambda) where possible - pay per use
* RDS with auto-scaling and stop/start scheduling
* Reserved capacity for predictable workloads
* S3 lifecycle policies for old data
* CloudWatch Logs retention policies

Deployment Environments
-----------------------

Development
^^^^^^^^^^^

* Local Docker Compose setup
* Minimal AWS resources (if needed)
* Separate AWS account or strict resource tagging

Staging
^^^^^^^

* Mirrors production architecture
* Used for testing before production deployment
* Can be stopped/started as needed to save costs

Production
^^^^^^^^^^

* Full production infrastructure
* High availability configuration
* Automated backups and disaster recovery

CI/CD Pipeline
--------------

GitHub Actions Workflow
^^^^^^^^^^^^^^^^^^^^^^^^

Planned workflow stages:

1. **Code Quality Checks**
   
   * Black formatting
   * Flake8 linting
   * MyPy type checking
   * Security scanning

2. **Testing**
   
   * Unit tests
   * Integration tests
   * E2E tests
   * Coverage reporting

3. **Build**
   
   * Build Docker image
   * Tag with commit SHA and version
   * Push to GitHub Container Registry

4. **Deploy to Staging**
   
   * Deploy to staging environment
   * Run smoke tests
   * Manual approval gate

5. **Deploy to Production**
   
   * Deploy to production
   * Health checks
   * Rollback on failure

Deployment Process
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Triggered on push to main branch
   git push origin main

   # Or manual deployment via GitHub Actions UI

Rollback Procedure
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Automatic rollback on health check failure
   # Manual rollback via GitHub Actions
   # Or using AWS console/CLI

Docker Deployment
-----------------

Production Docker Image
^^^^^^^^^^^^^^^^^^^^^^^

Build optimized production image:

.. code-block:: bash

   docker build --target production -t lineup:prod .

The production image:

* Uses multi-stage build
* Minimal base image (python:3.11-slim)
* Only production dependencies
* Non-root user for security
* Health check configured

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Required environment variables for production:

.. code-block:: bash

   FLASK_ENV=production
   SECRET_KEY=<secure-random-key>
   DATABASE_URL=<postgresql-connection-string>
   AWS_REGION=<aws-region>
   S3_BUCKET=<s3-bucket-name>

.. warning::
   Never hardcode secrets! Use AWS Secrets Manager or environment variables.

Security Considerations
-----------------------

Planned Security Measures
^^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Network Security**
   
   * VPC with private subnets for database
   * Security groups with least-privilege access
   * SSL/TLS for all connections

2. **Application Security**
   
   * JWT authentication
   * OAuth 2.0 integration
   * Input validation and sanitization
   * Rate limiting
   * CORS configuration

3. **Data Security**
   
   * Encrypted database connections
   * Encrypted data at rest (RDS encryption)
   * Encrypted backups
   * Secrets stored in AWS Secrets Manager

4. **Monitoring and Auditing**
   
   * CloudWatch Logs for all API requests
   * AWS CloudTrail for infrastructure changes
   * Security alerts for suspicious activity

Database Management
-------------------

Migrations
^^^^^^^^^^

Database migrations will use Alembic:

.. code-block:: bash

   # Create migration
   poetry run alembic revision --autogenerate -m "description"

   # Apply migrations
   poetry run alembic upgrade head

   # Rollback migration
   poetry run alembic downgrade -1

Backups
^^^^^^^

* **Automated backups** - Daily RDS snapshots
* **Retention** - 30 days
* **Point-in-time recovery** - Enabled
* **Manual backups** - Before major deployments

Monitoring and Logging
----------------------

Application Logging
^^^^^^^^^^^^^^^^^^^

Structured JSON logging to CloudWatch:

.. code-block:: python

   import logging
   import json

   logger = logging.getLogger(__name__)
   logger.info(json.dumps({
       "event": "lineup_created",
       "lineup_id": lineup_id,
       "timestamp": datetime.now().isoformat()
   }))

Metrics to Monitor
^^^^^^^^^^^^^^^^^^

* API request rate
* Response times
* Error rates
* Database connection pool
* Memory and CPU usage

Alerts
^^^^^^

* API error rate > 5%
* Response time > 1 second
* Database connection failures
* High memory/CPU usage
* Budget threshold breaches

Performance Optimization
------------------------

.. note::
   Performance optimization will be addressed in Phase 6.

Planned optimizations:

* Database query optimization
* Caching strategy (Redis)
* CDN for static files
* Connection pooling
* Async processing for PDF generation

Disaster Recovery
-----------------

Backup Strategy
^^^^^^^^^^^^^^^

* **Database**: Daily automated snapshots
* **Code**: Version control (GitHub)
* **Infrastructure**: Infrastructure as Code (Pulumi)
* **Secrets**: Backup in secure location

Recovery Procedures
^^^^^^^^^^^^^^^^^^^

1. **Database failure**: Restore from latest snapshot
2. **Application failure**: Rollback to previous version
3. **Infrastructure failure**: Redeploy using Pulumi
4. **Complete region failure**: Failover to backup region (future)

Recovery Time Objectives
^^^^^^^^^^^^^^^^^^^^^^^^

* **RTO** (Recovery Time Objective): < 1 hour
* **RPO** (Recovery Point Objective): < 1 hour (based on backup frequency)

Maintenance
-----------

Planned Maintenance Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Time**: Sundays 2:00 AM - 4:00 AM UTC
* **Frequency**: Monthly
* **Notice**: 1 week advance notice to users

Maintenance Procedures
^^^^^^^^^^^^^^^^^^^^^^

1. Notify users
2. Enable maintenance mode
3. Perform updates/maintenance
4. Run health checks
5. Disable maintenance mode
6. Verify functionality

Troubleshooting
---------------

Common Issues
^^^^^^^^^^^^^

**Application won't start**

* Check environment variables
* Verify database connectivity
* Check CloudWatch logs

**High error rate**

* Check CloudWatch logs for error details
* Verify database status
* Check for recent deployments

**Slow response times**

* Check database query performance
* Monitor CloudWatch metrics
* Review recent code changes

**Cost spike**

* Check Cost Explorer for details
* Review recent resource changes
* Verify budget alerts are working

Resources
---------

* AWS Documentation: https://docs.aws.amazon.com/
* Pulumi Documentation: https://www.pulumi.com/docs/
* GitHub Actions: https://docs.github.com/en/actions
* Docker Documentation: https://docs.docker.com/
