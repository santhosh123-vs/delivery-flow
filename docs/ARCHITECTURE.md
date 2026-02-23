# Architecture - DeliveryFlow

## Overview
DeliveryFlow is a modular CI/CD pipeline tool built with Python.

## Component Diagram

    +-------------------------------------------+
    |              CLI Interface                  |
    |            (Click-based CLI)                |
    +---------------------+---------------------+
                          |
    +---------------------v---------------------+
    |            Pipeline Engine                  |
    |    (Orchestrates stage execution)           |
    +--+--------+--------+--------+-------------+
       |        |        |        |
    +--v--+  +--v--+  +--v--+  +--v------+
    |Lint |  |Test |  |Build|  | Deploy  |
    |Stage|  |Stage|  |Stage|  | Stage   |
    +-----+  +-----+  +-----+  +---------+
                                    |
                              +-----v------+
                              | Rollback   |
                              | Manager    |
                              +------------+

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| YAML configs | Human-readable, version-controllable |
| Subprocess execution | Isolation, any command can run |
| Dependency graph | Stages run in correct order |
| Hook system | Extensible without modifying core |
| Dataclasses | Clean, typed data structures |
