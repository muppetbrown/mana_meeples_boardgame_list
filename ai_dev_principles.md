# AI Software Development Principles

> **Purpose:**  
> These principles define the standards for software written, refactored, or modified by an AI system.  
> They emphasize clarity, correctness, maintainability, and reasoning transparency.

---

## 🧠 Core Engineering Principles

### 1. Clarity Over Cleverness
- Write code that a human can understand immediately.  
- Avoid obscure tricks, nested complexity, or overly compact expressions.  
- Every variable, function, and class should clearly express its intent.

### 2. Single Responsibility
- Each function, class, or module must do **one logical task**.  
- Split or refactor when responsibilities mix (e.g., computation + I/O).  
- Prevent side effects that are not explicitly documented.

### 3. Consistency
- Apply uniform patterns for naming, error handling, and file structure.  
- Solve similar problems in similar ways.  
- Follow the project’s existing conventions unless there is a compelling reason to improve them.

### 4. Explicitness
- Make assumptions visible through parameters, configuration, or comments.  
- Avoid “magic numbers” or hidden state.  
- Prefer verbosity and predictability over implicit behavior.

### 5. Validation at Boundaries
- Validate all external data and API inputs before use.  
- Trust internal logic; never trust the outside world.  
- Return clear error messages on invalid input.

### 6. Fail Loudly, Log Clearly
- Detect and report errors early with detailed context.  
- Never suppress or silently ignore exceptions.  
- Ensure logs are human-readable and actionable.

### 7. Test for Behavior, Not Implementation
- Write or maintain tests that verify **outcomes**, not code structure.  
- Tests should fail only when observable behavior changes.  
- Maintain deterministic, self-contained test cases.

### 8. Iterate Safely
- Prefer incremental changes to large rewrites.  
- Keep commits atomic, reversible, and focused on one intent.  
- When refactoring, preserve functionality before improving structure.

### 9. Decouple and Reuse
- Minimize dependencies between modules.  
- Create reusable components with clear, documented interfaces.  
- Avoid tight coupling that reduces flexibility or testability.

### 10. Refactor Ruthlessly
- Once functionality works, simplify it.  
- Eliminate duplication, rename for clarity, and streamline logic.  
- “Working” is not the end; **maintainable** is.

---

## 🧭 Development Workflow Discipline

### 1. Assume Existing Implementation
Before creating any new code, **assume the functionality already exists** somewhere in the repository.

Steps:
1. **Search first:** Inspect related modules, utilities, or helper files for similar or partially implemented logic.  
2. **Check integration points:** Verify imports, routing, and usage paths — many “missing” features are simply disconnected or misreferenced.  
3. **Test and observe:** If something appears broken, test it in isolation or trace its data flow before rewriting.  
4. **Confirm redundancy:** Only proceed to new implementation if no working or recoverable code exists.

### 2. Modification Before Creation
If existing code:
- Is **not used**, fix the reference.  
- Is **not working**, debug or refactor it.  
- Is **pointing incorrectly**, repair the linkage.  
Only if all these fail and functionality is still missing, **request explicit approval** to create new code.

### 3. Avoid Parallel Functionality
Never duplicate existing logic under a new name or in a new file for convenience.  
When extending or fixing, modify or generalize the original implementation.

> New code creation is the **last resort**, not the default.  
> The AI must justify why modification was insufficient before generating new modules, functions, or files.

---

## ⚙️ Meta-Principles for AI Behavior

### A. Optimize for Human Understanding
Generate code that a competent engineer can read, extend, and debug with minimal guidance.

### B. Explain Reasoning
Before major code output or refactor, include a short explanation of *why* this approach was chosen.

### C. Prefer Safety Defaults
When uncertain between options:
- Choose explicit over implicit.  
- Choose safe over risky.  
- Choose maintainable over performant (unless performance is the primary goal).

### D. Detect and Remove Redundancy
Automatically identify and eliminate:
- Repeated logic  
- Unused imports or dead code  
- Duplicate function definitions or constants

### E. Continuous Verification
Before finalizing any change:
- Verify correctness through reasoning or tests.  
- Ensure prior assumptions remain valid.  
- Confirm the resulting code compiles, runs, and logically aligns with its purpose.

---

## ✅ Quality Checklist (For Every Commit)

| Category | Question |
|-----------|-----------|
| **Clarity** | Would a new developer understand this file without prior context? |
| **Scope** | Does each function do one coherent thing? |
| **Consistency** | Are naming and structure aligned with the rest of the project? |
| **Safety** | Are all external inputs validated and errors handled clearly? |
| **Reusability** | Could this code be reused without modification elsewhere? |
| **Verification** | Are behavior and tests still correct after the change? |

---

> “Good code explains itself. Great code teaches the next developer what *good* looks like.”
