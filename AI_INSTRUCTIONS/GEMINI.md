# AI Assistant Instructions

Your primary goal is to assist in the development of the current project. To do this effectively, you must ground all of your actions and responses in the project's established context.

## Critical First Steps

**Before doing ANY code development or dependency installation, you MUST:**

1. **Verify or Create Isolated Development Environment:**
   - **Python:** Check for `venv/` directory. If missing, run `python -m venv venv`
   - **Node.js:** Check for `node_modules/` and `package.json`
   - **Rust:** Verify `Cargo.toml` exists
   - **Go:** Verify `go.mod` exists
   - **Always activate the environment BEFORE installing dependencies or running code**

2. **Read and understand the following files in this order:**
   - **`VISION.md`**: To understand the project's core mission, goals, and principles.
   - **`DESIGN.md`**: To understand the technical architecture, development phases, and implementation details.
   - **`TODO.md`**: To see the list of current tasks and understand what needs to be done.
   - **`IDEAS.md`**: To understand what is considered out-of-scope for the current development phase.

These files are the single source of truth for the project. Do not deviate from the plans, principles, or architecture they describe without explicit instruction and confirmation. Your primary function is to help execute the plan laid out in these documents.
