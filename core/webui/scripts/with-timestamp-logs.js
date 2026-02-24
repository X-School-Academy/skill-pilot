#!/usr/bin/env node

const { spawn } = require("node:child_process");

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function pad2(value) {
  return String(value).padStart(2, "0");
}

function formatOffset(date) {
  const minutesEast = -date.getTimezoneOffset();
  const sign = minutesEast >= 0 ? "+" : "-";
  const absMinutes = Math.abs(minutesEast);
  const hours = Math.floor(absMinutes / 60);
  const minutes = absMinutes % 60;
  return `${sign}${pad2(hours)}${pad2(minutes)}`;
}

function formatTimestamp(date = new Date()) {
  const day = pad2(date.getDate());
  const month = MONTHS[date.getMonth()] || "Jan";
  const year = date.getFullYear();
  const hour = pad2(date.getHours());
  const minute = pad2(date.getMinutes());
  const second = pad2(date.getSeconds());
  const offset = formatOffset(date);
  return `[${day}/${month}/${year}:${hour}:${minute}:${second} ${offset}]`;
}

function streamWithTimestamp(stream, writer) {
  let carry = "";
  stream.on("data", (chunk) => {
    carry += chunk.toString("utf8");
    const lines = carry.split(/\r?\n/);
    carry = lines.pop() || "";
    for (const line of lines) {
      writer.write(`${formatTimestamp()} ${line}\n`);
    }
  });
  stream.on("end", () => {
    if (carry.length > 0) {
      writer.write(`${formatTimestamp()} ${carry}\n`);
    }
  });
}

const [mode = "dev", ...args] = process.argv.slice(2);
const nextCliPath = require.resolve("next/dist/bin/next");
const child = spawn(process.execPath, [nextCliPath, mode, ...args], {
  env: process.env,
  stdio: ["inherit", "pipe", "pipe"],
});

streamWithTimestamp(child.stdout, process.stdout);
streamWithTimestamp(child.stderr, process.stderr);

child.on("error", (error) => {
  console.error(`${formatTimestamp()} Failed to start Next.js: ${error.message}`);
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code || 0);
});
