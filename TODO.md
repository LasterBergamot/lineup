# Lineup Project - TODO

This TODO list is organized into phases based on the long-term plan outlined in `initial-instructions.md`.

## Phase 1: Project Foundation & Setup

- [x] **Phase 1.1**: Initialize Python project with Poetry for dependency management
  - [x] Create `pyproject.toml` with Poetry configuration
  - [x] Set up virtual environment
  - [x] Define initial dependencies (Flask, pytest, etc.)

- [x] **Phase 1.2**: Set up project structure (Flask API skeleton)
  - [x] Create directory structure (app/, tests/, docs/, etc.)
  - [x] Initialize Flask application
  - [x] Set up basic project configuration files

- [x] **Phase 1.3**: Configure code quality tools
  - [x] Set up flake8 with configuration file
  - [x] Set up black formatter with configuration
  - [x] Configure coverage.py for code coverage reporting

- [x] **Phase 1.4**: Set up testing framework (pytest with testing pyramid structure)
  - [x] Configure pytest with `pytest.ini` or `pyproject.toml`
  - [x] Set up test directory structure (unit, integration, e2e)
  - [x] Create initial test examples
  - [x] Configure test coverage reporting

- [ ] **Phase 1.5**: Configure containerization (Docker/podman)
  - [ ] Create Dockerfile for the application
  - [ ] Create docker-compose.yml for local development (with PostgreSQL)
  - [ ] Create .dockerignore file
  - [ ] Test container build and run

- [ ] **Phase 1.6**: Create initial documentation structure
  - [ ] Create comprehensive README.md
  - [ ] Set up Sphinx documentation structure
  - [ ] Configure Sphinx for API documentation
  - [ ] Create initial documentation pages

- [ ] **Phase 1.7**: Set up GitHub repository structure
  - [ ] Create GitHub Issues templates
  - [ ] Set up GitHub Projects board
  - [ ] Initialize GitHub Wiki structure
  - [ ] Create CONTRIBUTING.md (if applicable)

## Phase 2: Core API Development (Water Polo - Hungarian Leagues)

- [ ] **Phase 2.1**: Research and document the Rajtlista document structure
  - [ ] Access and analyze the document from waterpolo.hu/szovetseg/nyomtatvanyok
  - [ ] Document all required fields and sections
  - [ ] Create data model specifications
  - [ ] Note: Try to avoid storing document copy in repo if possible

- [ ] **Phase 2.2**: Design API endpoints for lineup creation (REST API design)
  - [ ] Design endpoint structure (RESTful conventions)
  - [ ] Define request/response schemas
  - [ ] Document endpoint specifications
  - [ ] Consider future generalization for other sports

- [ ] **Phase 2.3**: Implement validation layer
  - [ ] Set up input validation (using Flask validators or marshmallow/pydantic)
  - [ ] Implement business rule validation
  - [ ] Create custom validators for water polo specific rules
  - [ ] Add comprehensive error handling and messages

- [ ] **Phase 2.4**: Create data models for water polo lineups
  - [ ] Design models for players, teams, matches, lineups
  - [ ] Implement model classes (consider using SQLAlchemy models or Pydantic)
  - [ ] Add model validation
  - [ ] Design with generalization in mind for future sports

- [ ] **Phase 2.5**: Implement PDF generation for Rajtlista document
  - [ ] Choose PDF library (ReportLab, WeasyPrint, or similar)
  - [ ] Create PDF template matching Rajtlista format
  - [ ] Implement data-to-PDF mapping
  - [ ] Test PDF output format and printability

- [ ] **Phase 2.6**: Create OpenAPI specification
  - [ ] Generate OpenAPI/Swagger spec for all endpoints
  - [ ] Set up Swagger UI for API exploration
  - [ ] Document all request/response models
  - [ ] Include authentication requirements (for future phases)

- [ ] **Phase 2.7**: Write comprehensive tests
  - [ ] Unit tests for models and business logic
  - [ ] Integration tests for API endpoints
  - [ ] Test PDF generation
  - [ ] Test validation rules
  - [ ] Achieve high test coverage (>80%)

## Phase 3: Database Integration

- [ ] **Phase 3.1**: Set up PostgreSQL database schema
  - [ ] Design database schema (ERD diagram)
  - [ ] Define tables: players, teams, matches, lineups, etc.
  - [ ] Design with scalability and future sports in mind
  - [ ] Set up indexes and constraints

- [ ] **Phase 3.2**: Implement database models (SQLAlchemy/ORM)
  - [ ] Create SQLAlchemy models matching schema
  - [ ] Set up database connection and session management
  - [ ] Configure relationship mappings
  - [ ] Add model methods for common operations

- [ ] **Phase 3.3**: Create migration system (Alembic)
  - [ ] Initialize Alembic for database migrations
  - [ ] Create initial migration
  - [ ] Set up migration workflow
  - [ ] Document migration procedures

- [ ] **Phase 3.4**: Implement CRUD operations
  - [ ] Create operations for players
  - [ ] Create operations for teams
  - [ ] Create operations for matches
  - [ ] Create operations for lineups
  - [ ] Implement update and delete operations
  - [ ] Add proper error handling

- [ ] **Phase 3.5**: Add data persistence and recall functionality
  - [ ] Implement save/load functionality for lineups
  - [ ] Add data retrieval endpoints
  - [ ] Implement data versioning (if needed)
  - [ ] Add data export/import capabilities

- [ ] **Phase 3.6**: Write database integration tests
  - [ ] Set up test database
  - [ ] Write tests for all CRUD operations
  - [ ] Test database constraints and relationships
  - [ ] Test migration scripts
  - [ ] Test data integrity

## Phase 4: Cloud Deployment & CI/CD

- [ ] **Phase 4.1**: Set up AWS infrastructure (cost-optimized, using Pulumi for IaC)
  - [ ] Design AWS architecture (consider serverless for cost optimization)
  - [ ] Set up Pulumi project
  - [ ] Create infrastructure code (VPC, RDS, ECS/Lambda, etc.)
  - [ ] Configure cost-optimized resources (consider spot instances, reserved capacity)
  - [ ] Set up environment variables and secrets management
  - [ ] **Set up comprehensive cost management and protection** (prevent unexpected charges)
    - [ ] Configure AWS Budgets with automatic actions (shutdown resources when budget exceeded)
    - [ ] Set up AWS Cost Anomaly Detection for unusual spending patterns
    - [ ] Create billing alarms in CloudWatch (multiple thresholds: 50%, 80%, 100% of budget)
    - [ ] Implement automatic resource shutdown via Lambda functions triggered by budget alerts
    - [ ] Set up EventBridge rules to automatically stop/terminate non-essential resources on budget threshold
    - [ ] Configure resource tagging strategy for cost tracking and automated shutdowns
    - [ ] Create Lambda function to automatically stop EC2 instances, RDS databases, and other resources when budget exceeded
    - [ ] Set up spending limits where possible (note: AWS doesn't have hard spending limits, but budgets with actions can simulate this)
    - [ ] Configure automatic shutdown of development/staging environments during off-hours (if applicable)
    - [ ] Document cost management strategy and emergency shutdown procedures
    - [ ] Test automatic shutdown mechanisms in a safe environment before production

- [ ] **Phase 4.2**: Configure GitHub Actions for CI/CD pipeline
  - [ ] Create CI workflow (lint, test, build)
  - [ ] Create CD workflow (deploy to staging/production)
  - [ ] Set up secrets in GitHub
  - [ ] Configure automated testing on PRs
  - [ ] Add deployment approvals

- [ ] **Phase 4.3**: Set up code quality checks in builds (local and CI)
  - [ ] Create scripts for running checks locally (check.sh, check.ps1)
  - [ ] Integrate code quality checks into CI workflow (Black, Flake8, MyPy)
  - [ ] Configure checks to run on every build (local and CI)
  - [ ] Ensure checks block builds/merges if they fail
  - [ ] Document how to run checks locally

- [ ] **Phase 4.4**: Set up GitHub Packages as artifact repository
  - [ ] Configure GitHub Packages for Docker images
  - [ ] Set up package publishing in CI/CD
  - [ ] Configure package access and permissions

- [ ] **Phase 4.5**: Create Docker images and container orchestration
  - [ ] Optimize Dockerfile for production
  - [ ] Set up multi-stage builds
  - [ ] Configure container orchestration (ECS, EKS, or similar)
  - [ ] Set up health checks and monitoring

- [ ] **Phase 4.6**: Configure deployment pipeline
  - [ ] Set up staging environment
  - [ ] Set up production environment
  - [ ] Configure blue-green or rolling deployments
  - [ ] Set up rollback procedures
  - [ ] Document deployment process

- [ ] **Phase 4.7**: Set up monitoring and logging
  - [ ] Configure CloudWatch or similar monitoring
  - [ ] Set up application logging
  - [ ] Create dashboards for key metrics
  - [ ] Set up alerts for critical issues
  - [ ] Configure log retention policies

## Phase 5: Security Implementation

- [ ] **Phase 5.1**: Implement JWT authentication
  - [ ] Choose JWT library and implement token generation
  - [ ] Create authentication endpoints (login, refresh, logout)
  - [ ] Implement token validation middleware
  - [ ] Set up secure token storage and transmission
  - [ ] Configure token expiration and refresh logic

- [ ] **Phase 5.2**: Set up OAuth integration (Google accounts)
  - [ ] Register application with Google OAuth
  - [ ] Implement OAuth flow
  - [ ] Handle OAuth callbacks
  - [ ] Link OAuth accounts to user system
  - [ ] Test OAuth flow end-to-end

- [ ] **Phase 5.3**: Add authorization and access control
  - [ ] Implement role-based access control (RBAC)
  - [ ] Create permission system
  - [ ] Add authorization checks to endpoints
  - [ ] Implement user management endpoints
  - [ ] Add audit logging for security events

- [ ] **Phase 5.4**: Implement security best practices
  - [ ] Add input sanitization and validation
  - [ ] Implement rate limiting
  - [ ] Configure CORS properly
  - [ ] Add HTTPS/TLS enforcement
  - [ ] Implement SQL injection prevention
  - [ ] Add XSS protection
  - [ ] Configure security headers
  - [ ] Set up dependency vulnerability scanning

- [ ] **Phase 5.5**: Security audit and penetration testing
  - [ ] Conduct security code review
  - [ ] Run automated security scanning tools
  - [ ] Perform penetration testing
  - [ ] Address identified vulnerabilities
  - [ ] Document security measures

- [ ] **Phase 5.6**: Update documentation with security guidelines
  - [ ] Document authentication flow
  - [ ] Document authorization model
  - [ ] Create security best practices guide
  - [ ] Document incident response procedures

## Phase 6: API Finalization & Frontend Preparation

- [ ] **Phase 6.1**: Finalize API endpoints and documentation
  - [ ] Review and refine all endpoints
  - [ ] Ensure API consistency
  - [ ] Add missing endpoints if needed
  - [ ] Update OpenAPI specification

- [ ] **Phase 6.2**: Create comprehensive API documentation (Sphinx + Read The Docs)
  - [ ] Complete Sphinx documentation
  - [ ] Set up Read The Docs integration
  - [ ] Write detailed API usage examples
  - [ ] Create getting started guide
  - [ ] Document error codes and responses

- [ ] **Phase 6.3**: Add API testing tools setup (Bruno)
  - [ ] Create Bruno collection for API testing
  - [ ] Add all endpoint examples
  - [ ] Include authentication examples
  - [ ] Document Bruno setup in README

- [ ] **Phase 6.4**: Create architectural diagrams
  - [ ] Create system architecture diagram
  - [ ] Create data flow diagrams
  - [ ] Create API endpoint flow diagrams
  - [ ] Create database schema diagram
  - [ ] Create deployment architecture diagram
  - [ ] Use mermaid or similar for diagrams

- [ ] **Phase 6.5**: Prepare API for frontend integration
  - [ ] Ensure CORS is properly configured
  - [ ] Add frontend-friendly response formats
  - [ ] Create API client examples (if needed)
  - [ ] Document frontend integration guide
  - [ ] Test API with frontend mockup

- [ ] **Phase 6.6**: Performance optimization and scalability considerations
  - [ ] Conduct performance testing
  - [ ] Optimize database queries
  - [ ] Implement caching where appropriate
  - [ ] Add pagination for list endpoints
  - [ ] Optimize PDF generation performance
  - [ ] Document scalability considerations
  - [ ] Plan for future scaling needs

## Notes

- **Generalization**: Keep in mind that the system should be designed to support other sports in the future. Abstract common functionality where possible.
- **Security**: High emphasis on security throughout all phases. Review security implications of each feature.
- **Code Quality**: Maintain high code quality standards throughout development. Use code reviews (Cursor Bugbot) and automated tools.
- **Documentation**: Keep documentation up-to-date as the project evolves.
- **Testing**: Maintain high test coverage and test at all levels of the testing pyramid.

## References

- Initial instructions: `initial-instructions.md`
- Rajtlista document: https://waterpolo.hu/szovetseg/nyomtatvanyok
- Project repository: This repository (API only, frontend in separate repo)
