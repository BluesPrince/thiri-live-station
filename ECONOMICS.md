# 24/7 Agentic Radio Station: Cloud Economics & Bandwidth Math

## The 24/7 Egress Reality

When running a 24/7 live video stream, bandwidth (network egress) is the single largest operating expense if hosted on standard cloud container platforms.

### Monthly Egress Volume Calculation
- Video Bitrate: 2,500 kbps (H.264 720p/1080p)
- Audio Bitrate: 160 kbps (AAC stereo)
- Combined Bitrate: 2,660 kbps = 332.5 KB/second
- Per Hour: 332.5 KB/s * 3,600 s = ~1.197 GB/hour
- Per Day: 1.197 GB * 24 h = ~28.7 GB/day
- Per Month (30 Days): 28.7 GB * 30 days = **~862 GB / month**

---

## Cost Comparison by Provider

| Platform | Compute Tier | Egress Allowance | Egress Over-Quota Rate | Estimated Monthly Bill |
| :--- | :--- | :--- | :--- | :--- |
| **AWS Lightsail** | 1 vCPU, 1 GB RAM | **1,000 GB (1 TB) included** | \$0.09 / GB | **\$5.00 flat** |
| **Hetzner Cloud CX22** | 2 vCPU, 4 GB RAM | **20,000 GB (20 TB) included** | €1.00 / TB | **€3.79 (~$4.10) flat** |
| **Railway (Full Stream)** | Pro Plan Container | 100 GB included | \$0.05 / GB (~762 GB billable) | **\$38.10 - \$45.00** |
| **AWS ECS / Fargate** | 1 vCPU, 1 GB RAM | 100 GB free tier | \$0.09 / GB (~762 GB billable) | **\$68.50 - \$80.00** |

---

## The Hybrid Architectural Blueprint

To achieve production-grade reliability while capping costs at **\$5.00 to \$10.00 / month**:

1. **Heavy RTMP Broadcast Node (\$5.00 flat)**:
   - Deploy Docker container with FFmpeg + Python DSP on AWS Lightsail or Hetzner CX22.
   - 1 TB egress covers the entire 862 GB monthly broadcast with zero overages.

2. **Control Plane & Agent Services (\$0.00 to \$5.00)**:
   - Deploy chat parsing daemon, state webhooks, or API management on Railway or serverless functions.
   - Low bandwidth (< 50 MB / month) fits within free or base tiers.

3. **Audio Synthesis & TTS Optimization (\$0.00 - \$5.00)**:
   - All instruments (Rhodes, Felt Piano, Sine Sub, 432 Hz bowls, vinyl bed) synthesized procedurally with pure NumPy: **\$0.00 API cost**.
   - ElevenLabs voice affirmations cached locally by text MD5 hash: each unique affirmation is synthesized once and reused forever.
