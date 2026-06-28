# Aether Demos

Screen recordings that walk through Aether's core flows. Each demo below has a storyboard so the clip stays focused and reproducible.

## How to add a video

GitHub renders inline videos in Markdown when they are hosted on the GitHub user-content CDN:

1. Open a draft issue or PR comment in the repo.
2. Drag the `.mp4`/`.mov`/`.webm` file into the comment box. GitHub uploads it and returns a URL like
   `https://github.com/JustNavaneethStuff/Aether/assets/<user-id>/<uuid>.mp4`.
3. Paste that URL on its own line under the matching demo below (GitHub auto-embeds a player).

Alternatively, commit the file under `docs/demos/` and link it relatively (note: large binaries inflate the repo; prefer the CDN approach or [Git LFS](https://git-lfs.com/)).

Keep clips to 60-90 seconds. Record at 1280x720 or higher.

## 1. End-to-end orchestration

**Goal:** show a request flowing through the gateway, orchestrator, planner, and specialized agents with SSE streaming.

Storyboard:
1. `make up` to start the stack.
2. `POST /v1/conversations` to create a conversation.
3. `POST /v1/conversations/{id}/messages` with an analytical prompt; show the streamed SSE tokens.
4. `GET /v1/agents` to show the registered replaceable agents.

<!-- Paste video URL below this line -->

## 2. Async workflows (Atlas Queue integration)

**Goal:** show a long-running workflow submitted as a background job.

Storyboard:
1. Default `TASK_QUEUE_BACKEND=local` runs inline.
2. `POST /v1/orchestrate/async` returns a `job_id` and state.
3. (Optional) Set `TASK_QUEUE_BACKEND=atlas` with Atlas Queue running, then show the task in Atlas's dashboard and the `job.completed` event in Aether.

<!-- Paste video URL below this line -->

## 3. Knowledge acquisition (Argus integration)

**Goal:** show external knowledge acquisition feeding RAG.

Storyboard:
1. Invoke the `web_crawl` tool through the tool-executor.
2. `POST /v1/acquire` on the knowledge-service to trigger a crawl.
3. `GET /v1/datasets/{id}` to retrieve structured results.
4. (Optional) With `KNOWLEDGE_BACKEND=argus`, show the crawl appearing in Argus's dashboard.

<!-- Paste video URL below this line -->

## 4. Observability

**Goal:** show the operability story for CloudForge deployments.

Storyboard:
1. `make up-obs` to start Prometheus and Grafana.
2. Open the Phase 3 Grafana dashboard.
3. Run a workflow and watch agent latency, LLM cost, evaluations, and approval metrics update.

<!-- Paste video URL below this line -->
