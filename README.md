# DevOps Services Docker Compose

이 프로젝트는 Jenkins, OpenGrok, Jenkins Dashboard, Nginx를 포함한 완전한 DevOps 환경을 Docker Compose로 구성합니다.

## 🚀 빠른 시작

```bash
# 저장소 클론
git clone https://github.com/nicolaschoi7042/servicedocker.git
cd servicedocker

# 서비스 시작
docker compose up -d

# 로그 확인
docker compose logs -f
```

## 📋 서비스 목록

- **Jenkins**: CI/CD 파이프라인 (포트: 5000, 50000)
- **OpenGrok**: 소스코드 검색 (포트: 8081)
- **Jenkins Dashboard**: 작업 모니터링 (포트: 3000)
- **OpenGrok LDAP Auth**: LDAP 인증 서비스 (포트: 8000)
- **Nginx**: 리버스 프록시 및 SSL (포트: 80, 443, 8080)

## 📂 데이터 볼륨

중요한 데이터는 `/data` 디렉토리에 저장됩니다:

```
/data/
├── jenkins/     # Jenkins 홈 디렉토리
├── nginx/       # Nginx 설정 및 SSL 인증서
└── opengrok/    # OpenGrok 소스코드 및 인덱스
```

## 🔧 설정

### LDAP 인증
- 외부 LDAP 서버: `172.30.1.97:389`
- 도메인: `roboetech.com`

### 네트워크
- `docker_devops_bridge`: 메인 네트워크
- `opengrok_docker_devops_bridge`: OpenGrok 전용 네트워크

## 📖 자세한 문서

상세한 분석 및 운영 가이드는 [claude.md](claude.md) 파일을 참조하세요.

## 🤝 기여

이슈나 개선사항이 있으시면 GitHub Issues를 통해 알려주세요.