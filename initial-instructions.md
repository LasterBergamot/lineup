# Lineup Project - Initial instructions

## Rules
- Do not generate anything without my permission!
- Everything here is from a bird's-eye view, we'll get into the details later during the development

## Idea
The purpose of this project is have a webapp where lineups for teams of different sports can be created for certain matches and the related official document can be exported in a printable format, e.g. pdf.

Initially, the project is about water polo and in that the Hungarian leagues, governed by the Magyar Vízilabda Szövetség. That would be the first main task, e.g. epic, to tackle. Later other sports can come into the picture, so whatever can be generalized, generalize it.

The document this project will fill in later with the lineups and other details can be found on this page https://waterpolo.hu/szovetseg/nyomtatvanyok and it's called Rajtlista. It would be great if no copy of that document would reside in this repo, but if there's no other way, then it's fine to save a copy for later use.

This repository would be an API, - REST, GraphQL, etc. - that would be called by the webapp later.

The whole app, including the FE, will be used be very few people initially, and the app doesn't need to run all the time.

Other details are mentioned below.

## Tech Stack
- Backend: Python
- Potential frontend in another repo: ReactJS, but other options can come in as well, like Django, if we want to stay with Python
- DB: PostgreSQL or some other relational DB, but other options can come in as well - NocoDB or AWS DynamoDB?
- API implementation: Flask, or some other option with validation in place
- CI/CD: Github Actions
- Artifactory: Github packages
- Infrastructure as Code: Pulumi?
- API tool: Bruno
- Cloud: AWS, with as less costs as possible
- Documentation: readme in the repos + Github wiki - in this project, Sphinx + Read The Docs? + create OpenAPI specs + create diagrams to illustrate flow wherever possible
- Tickets: Github projects and issues
- Security: JWT or something else? + high emphasis on this, make the app meet the high security standards
- Code quality: flake8, black, coverage + others
- Dependency management: Poetry or something else
- Code reviews: Cursor Bugbot
- Testing: pytest, some automated test tools for every level of the testing pyramid
- Containerization: Docker or podman

## Key Points
- very few (around 5) users in the beginning, but keep potential scalability in mind for later
- the app would be only needed a couple of times in a month initially
- high emphasis on security to meet standards

## Long Term Plan
1. Create API in this repository to be able to fill in the required details for the lineup and other details required in the given document. The initial project should have everything lined up for code quality, containerization, tests, and dependency management.
2. The API should have validation in place to leave user error out of the picture
3. Once we know the API works is it should, the DB can come in, so every data of a document can be recalled later. This applies to players, teams, and some other data, so it would be reusable later.
4. The app should be able to run in the cloud without any problem. CI/CD should be put in place as well.
5. Once the app works, we can add security and some kind of sign in options maybe via OAuth using Google accounts, for example.
6. The fully fledged API then can be called by the FE app, which will be put together in another repo.