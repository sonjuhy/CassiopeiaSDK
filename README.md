# Cassiopeia Agent SDK

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/img/cassiopeia_white.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/img/cassiopeia_black.png">
    <img alt="Cassiopeia Logo" src="assets/img/cassiopeia_black.png" width="300">
  </picture>
</p>

[English](#english) | [한국어](#한국어)

<a name="english"></a>
## English

### Overview
Cassiopeia Agent SDK is a monorepo containing the official SDKs (Node.js and Python) for the Cassiopeia Agent framework. 
This SDK allows developers in no-code or vibe-coding environments to easily build agents that communicate with the Cassiopeia orchestra and execute tools using a single library.

It completely abstracts the complexities of the communication protocol (Redis Pub/Sub), permission management, and error handling, allowing developers to focus solely on business logic and prompt engineering.

### Repository Structure
This repository is structured as a monorepo containing SDKs for multiple languages:

*   [`/node`](./node/): The official Node.js SDK.
*   [`/python`](./python/): The official Python SDK.
*   [`GUIDE.md`](./GUIDE.md): Detailed usage guide and architecture explanation.
*   [`SPEC.md`](./SPEC.md): Technical specifications and requirements.

### Quick Start
To get started with a specific language, please navigate to the respective directory and follow the instructions in its `README.md`.

*   **For Node.js Developers:** See the [Node.js SDK Documentation](./node/README.md).
*   **For Python Developers:** See the [Python SDK Documentation](./python/README.md).

### License
This project is licensed under the Apache License 2.0 - see the [LICENSE](./LICENSE) file for details.

---

<a name="한국어"></a>
## 한국어

### 개요
Cassiopeia Agent SDK는 Cassiopeia 에이전트 프레임워크를 위한 공식 SDK(Node.js 및 Python)를 포함하는 모노레포(Monorepo)입니다.
노코드(No-code) 혹은 바이브 코딩(Vibe-coding) 환경의 개발자가 단 하나의 라이브러리만으로 오케스트라(Cassiopeia)와 통신하고 도구를 호출하는 에이전트를 손쉽게 빌드할 수 있도록 돕습니다.

통신 규격(Redis Pub/Sub), 권한 관리, 에러 처리 등의 복잡성을 라이브러리가 완전히 추상화하여, 개발자는 비즈니스 로직과 프롬프트 엔지니어링에만 집중할 수 있습니다.

### 저장소 구조
이 저장소는 여러 언어를 지원하는 SDK를 포함하는 모노레포 구조로 되어 있습니다:

*   [`/node`](./node/): 공식 Node.js SDK.
*   [`/python`](./python/): 공식 Python SDK.
*   [`GUIDE.md`](./GUIDE.md): 상세 활용 가이드 및 아키텍처 설명.
*   [`SPEC.md`](./SPEC.md): 기술 스펙 및 요구사항 정의.

### 시작하기
특정 언어로 개발을 시작하려면 해당 디렉터리로 이동하여 `README.md`의 안내를 따르세요.

*   **Node.js 개발자:** [Node.js SDK 문서](./node/README.md)를 확인하세요.
*   **Python 개발자:** [Python SDK 문서](./python/README.md)를 확인하세요.

### 라이선스
이 프로젝트는 Apache License 2.0에 따라 라이선스가 부여됩니다. 자세한 내용은 [LICENSE](./LICENSE) 파일을 참조하세요.