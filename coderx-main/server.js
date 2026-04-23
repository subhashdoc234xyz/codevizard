require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const { spawn } = require('child_process');
const fs = require('fs');
const cors = require('cors');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const app = express();
app.use(cors());

// --- ADDED THIS LINE ---
app.use(express.static('public'));
// -----------------------

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

const PORT = process.env.PORT || 5000;

// Gemini API Setup
const apiKeys = [
    process.env.gemini_key_1,
    process.env.gemini_key_2,
    process.env.gemini_key_3,
    process.env.gemini_key_4,
    process.env.gemini_key_5,
    process.env.gemini_key_6
].filter(Boolean);

let currentKeyIndex = 0;

io.on('connection', (socket) => {
    let process = null;
    let silenceTimer = null;

    const startSilenceDetection = () => {
        if (silenceTimer) clearTimeout(silenceTimer);
        silenceTimer = setTimeout(() => {
            if (process && process.exitCode === null) {
                socket.emit('input_required');
            }
        }, 150); // 150ms of silence = program is waiting for input
    };

    socket.on('run_code', async ({ code, language }) => {
        if (apiKeys.length === 0) {
            socket.emit('output', 'No Gemini API keys found in .env\n');
            socket.emit('finished', 1);
            return;
        }

        let fullPrompt = `You are a code execution engine. The user has provided code in ${language}. Simulate the execution of this code and provide the exact standard output (and standard error, if any) that this code would produce when run. DO NOT provide any markdown, explanations, or code blocks. ONLY return the output as plain text. If the code requires inputs (like Scanner, cin, input()), YOU MUST CHOOSE reasonable sample inputs yourself and pretend the user typed them. DO NOT throw EOF errors or exceptions. Simulate a completely successful run with your chosen inputs. Keep your chosen inputs simple and realistic. Print the inputs in the output as if they were echoed in the terminal.

CODE:
${code}`;

        let success = false;
        for (let i = 0; i < apiKeys.length; i++) {
            try {
                const genAI = new GoogleGenerativeAI(apiKeys[currentKeyIndex]);
                const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });
                
                const result = await model.generateContentStream(fullPrompt);
                for await (const chunk of result.stream) {
                    const chunkText = chunk.text();
                    socket.emit('output', chunkText);
                }
                socket.emit('finished', 0);
                success = true;
                break;
            } catch (error) {
                const errorMsg = error.toString().toLowerCase();
                if (errorMsg.includes("429") || errorMsg.includes("exhausted") || errorMsg.includes("quota")) {
                    console.log(`⚠️ Key ${currentKeyIndex + 1} exhausted. Switching to next key...`);
                    currentKeyIndex = (currentKeyIndex + 1) % apiKeys.length;
                    continue;
                } else {
                    socket.emit('output', `\n[System Error]: ${error.toString()}`);
                    socket.emit('finished', 1);
                    success = true;
                    break;
                }
            }
        }
        
        if (!success) {
            socket.emit('output', `\n[System Error]: All API keys have reached their free tier limits!`);
            socket.emit('finished', 1);
        }
    });

    socket.on('submit_input', (input) => {
        if (process) {
            process.stdin.write(input + "\n");
            socket.emit('output', input + "\n"); // Show what user typed
            startSilenceDetection(); // Restart wait timer for loops
        }
    });

    socket.on('disconnect', () => {
        if (process) process.kill();
    });
});

server.listen(PORT, () => console.log(`Compiler Server running on port ${PORT}`));