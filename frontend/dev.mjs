// Dev launcher: starts the Python FastAPI backend and the Vite dev server together.
//
// v0's preview (and `pnpm dev`) only runs a single command. The frontend proxies
// API routes to the v2 FastAPI backend on port 8000.
//
// This script bootstraps a Python virtualenv (once), installs requirements, then
// runs uvicorn and vite side by side, forwarding their output and shutdown signals.

import { spawn } from "node:child_process"
import { existsSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const frontendDir = dirname(fileURLToPath(import.meta.url))
const rootDir = join(frontendDir, "..")
const venvDir = join(rootDir, ".venv")
const isWindows = process.platform === "win32"
const venvPython = join(venvDir, isWindows ? "Scripts" : "bin", isWindows ? "python.exe" : "python")
const BACKEND_PORT = process.env.BACKEND_PORT || "8000"

const children = []
let shuttingDown = false

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: "inherit", ...options })
    child.on("error", reject)
    child.on("exit", (code) => {
      if (code === 0) resolve()
      else reject(new Error(`${command} ${args.join(" ")} exited with code ${code}`))
    })
  })
}

async function ensureBackendDeps() {
  const pythonBin = process.env.PYTHON_BIN || "python3"
  if (!existsSync(venvPython)) {
    console.log("[dev] Creating Python virtualenv at .venv ...")
    await run(pythonBin, ["-m", "venv", venvDir])
  }
  console.log("[dev] Installing backend requirements (this runs only when needed) ...")
  await run(venvPython, ["-m", "pip", "install", "--quiet", "--upgrade", "pip"])
  await run(venvPython, ["-m", "pip", "install", "--quiet", "-r", join(rootDir, "requirements.txt")])
}

function startProcess(name, command, args, options = {}) {
  const child = spawn(command, args, { stdio: "inherit", ...options })
  children.push(child)
  child.on("exit", (code) => {
    if (!shuttingDown) {
      console.log(`[dev] ${name} exited with code ${code}, shutting down.`)
      shutdown(code ?? 1)
    }
  })
  return child
}

function shutdown(code) {
  if (shuttingDown) return
  shuttingDown = true
  for (const child of children) {
    if (!child.killed) child.kill("SIGTERM")
  }
  process.exit(code)
}

process.on("SIGINT", () => shutdown(0))
process.on("SIGTERM", () => shutdown(0))

async function main() {
  try {
    await ensureBackendDeps()
  } catch (error) {
    console.error("[dev] Failed to bootstrap the Python backend:", error.message)
    process.exit(1)
  }

  startProcess(
    "backend",
    venvPython,
    ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", BACKEND_PORT, "--reload"],
    { cwd: rootDir },
  )

  startProcess("frontend", "pnpm", ["exec", "vite"], { cwd: frontendDir })
}

main()
