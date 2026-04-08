<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=transparent&height=120&text=CareFlow&fontSize=60&fontColor=4285F4&fontAlignY=40&desc=Multi-Agent%20Healthcare%20Post-Visit%20Care%20Coordinator&descSize=16&descAlignY=75&descColor=555555" width="100%" />
</p>

<p align="center">
  <em>One doctor visit. Eight AI agents. Continuous care.</em>
</p>

<p align="center">
  <a href="https://careflow-892626469440.us-central1.run.app">
    <img src="https://img.shields.io/badge/Live_Demo-CareFlow-4285F4?style=flat-square&logo=googlecloud&logoColor=white" />
  </a>
  <a href="https://youtu.be/jn-dIMSrUts">
    <img src="https://img.shields.io/badge/Demo_Video-YouTube-FF0000?style=flat-square&logo=youtube&logoColor=white" />
  </a>
  <a href="Inference_Engines_GenAI_Hackathon.pdf">
    <img src="https://img.shields.io/badge/Presentation-PDF-B7472A?style=flat-square&logo=adobeacrobatreader&logoColor=white" />
  </a>
  <a href="https://vision.hack2skill.com/event/apac-genaiacademy">
    <img src="https://img.shields.io/badge/APAC_Academy-Hackathon-FBBC04?style=flat-square&logo=google&logoColor=white" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Agents-8-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/Safety-7_Layers-34A853?style=flat-square" />
  <img src="https://img.shields.io/badge/Intents-9-8E75B2?style=flat-square" />
  <img src="https://img.shields.io/badge/Tests-94_Passed-blue?style=flat-square" />
</p>

---

## The Problem

- **537 million** adults worldwide live with diabetes — projected to reach 783M by 2045
- **50%** of chronic disease patients stop following treatment plans within 6 months
- The gap between "what the doctor said" and "what the patient actually does" costs **$528B annually** in preventable complications

## The Solution

CareFlow bridges the post-visit care gap with **8 specialized AI agents** orchestrated by a single `root_agent`, routing across 9 intent categories with real infrastructure — AlloyDB, 3 MCP integrations, and Agentic RAG.

<table>
<tr>
<td align="center" width="25%"><b>8 AI Agents</b><br>Smart routing care team</td>
<td align="center" width="25%"><b>7-Layer Safety</b><br>Medical-grade protection</td>
<td align="center" width="25%"><b>Agentic RAG</b><br>HyDE + Hybrid + Self-RAG</td>
<td align="center" width="25%"><b>Real Data</b><br>AlloyDB + pgvector</td>
</tr>
<tr>
<td align="center"><b>3 MCP Tools</b><br>Calendar, Gmail, DB</td>
<td align="center"><b>Voice I/O</b><br>STT + TTS</td>
<td align="center"><b>Drug Interaction</b><br>openFDA 3-layer cascade</td>
<td align="center"><b>Health Charts</b><br>BP, glucose, weight</td>
</tr>
</table>

## Architecture

<p align="center">
  <img src="diagrams/careflow_architecture_overview.webp" alt="CareFlow Architecture" width="520" />
</p>

### Agentic RAG Pipeline

```mermaid
flowchart LR
    Q["Query"] --> H["HyDE\nGemini Flash"]
    H --> D["Dense Search\npgvector + HNSW"]
    H --> B["Sparse Search\nBM25"]
    D & B --> R["RRF Fusion\nk=60"]
    R --> S["Self-RAG\nReflection"]
    S --> C{"Confidence"}
    C -->|"≥ 0.78"| HIGH["Full Answer"]
    C -->|"0.6 - 0.78"| MED["Hedged Answer"]
    C -->|"< 0.6"| LOW["Refuse"]
```

## Tech Stack

**AI & Backend**

<img src="https://img.shields.io/badge/Google ADK-4285F4?style=flat-square&logo=googlecloud&logoColor=white"> <img src="https://img.shields.io/badge/Gemini 2.5-8E75B2?style=flat-square&logo=google&logoColor=white"> <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white"> <img src="https://img.shields.io/badge/MCP Protocol-FF6F00?style=flat-square&logo=googlecloud&logoColor=white">

**Data & Infrastructure**

<img src="https://img.shields.io/badge/AlloyDB-34A853?style=flat-square&logo=postgresql&logoColor=white"> <img src="https://img.shields.io/badge/pgvector-336791?style=flat-square&logo=postgresql&logoColor=white"> <img src="https://img.shields.io/badge/Cloud Run-4285F4?style=flat-square&logo=googlecloud&logoColor=white"> <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white">

**Frontend**

<img src="https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=white"> <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white"> <img src="https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white">

---

*Built for Google Cloud Gen AI Academy APAC — Cohort 1 Hackathon*
