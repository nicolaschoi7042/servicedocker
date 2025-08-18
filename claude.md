# DevOps 환경 Docker Compose 프로젝트 분석

## 🎯 프로젝트 개요

이 프로젝트는 Jenkins CI/CD, OpenGrok 코드 검색, Jenkins Dashboard, 그리고 Nginx 리버스 프록시를 통합한 완전한 DevOps 환경을 Docker Compose로 구성합니다. LDAP 인증을 통한 중앙 집중식 사용자 관리와 SSL 인증서를 적용한 보안 환경을 제공합니다.

## 🏗️ 아키텍처 분석

### 서비스 구성도
```
[Internet] → [Nginx (SSL/443,80,8080)] → [Jenkins (5000), OpenGrok (8081), Dashboard (3000)]
                         ↓
[LDAP Auth Service] ← → [OpenLDAP]
```

### 핵심 서비스

#### 1. **Jenkins** (`jenkins`)
- **이미지**: `docker-jenkins`
- **포트**: `5000:8080` (웹 UI), `50000:50000` (에이전트 연결)
- **역할**: CI/CD 파이프라인 관리
- **데이터 볼륨**: `/data/jenkins` → `/var/jenkins_home`
- **특징**:
  - 한국 시간대 설정 (`Asia/Seoul`)
  - 다양한 플러그인 설치 (Git, Gradle, Pipeline, LDAP 등)
  - 자동 재시작 (`unless-stopped`)

#### 2. **OpenGrok** (`opengrok`)
- **이미지**: `opengrok/docker:latest`
- **포트**: `8081:8080`
- **역할**: 소스코드 검색 및 브라우징
- **데이터 볼륨**: 
  - `/data/opengrok/src` (소스코드)
  - `/data/opengrok/data` (인덱스)
  - `/data/opengrok/etc` (설정)
  - `/data/opengrok/bin` (실행파일)
- **특징**: 
  - moros, morow 프로젝트 코드 인덱싱
  - SSH 키 접근 (`/.ssh`)

#### 3. **Jenkins Dashboard** (`jenkins-dashboard`)
- **이미지**: `jenkins-dashboard-jenkins-dashboard`
- **포트**: `3000:3000`
- **역할**: Jenkins 작업 모니터링 대시보드
- **특징**:
  - LDAP 인증 통합
  - Jenkins API 연동
  - Next.js 기반 React 애플리케이션

#### 4. **Nginx** (`nginx`)
- **이미지**: `opengrok-nginx`
- **포트**: `80:80`, `443:443`, `8080:8080`
- **역할**: 리버스 프록시 및 SSL 터미네이션
- **설정 파일**: `/data/nginx/conf.d`
- **SSL 인증서**: `/data/nginx/sslcert`
- **인증**: `/data/nginx/htpasswd`

#### 5. **OpenGrok LDAP Auth** (`opengrok-ldap-auth`)
- **이미지**: `opengrok-ldap-auth`
- **포트**: `8000:8000`
- **역할**: OpenGrok LDAP 인증 프록시
- **외부 LDAP 서버**: `172.30.1.97:389`
- **도메인**: `roboetech.com`
- **특징**: 외부 LDAP 서버와 OpenGrok 간 인증 브리지

## 🌐 네트워크 구성

### 네트워크 토폴로지
```
docker_devops_bridge (172.18.0.0/16)
├── jenkins (172.18.0.4)
├── dashboard (172.18.0.5)
└── opengrok-ldap-auth (172.18.0.3)

opengrok_docker_devops_bridge (172.20.0.0/16)
├── opengrok (172.20.0.3)
├── nginx (172.20.0.6)
├── jenkins (172.20.0.4)
├── dashboard (172.20.0.2)
└── opengrok-ldap-auth (172.20.0.5)

External LDAP Server: 172.30.1.97:389
```

### 네트워크 특징
- **이중 네트워크**: 서비스 간 유연한 통신을 위한 멀티네트워크 구성
- **외부 네트워크**: 기존 네트워크 재사용으로 다운타임 없는 배포

## 💾 데이터 관리

### 중요 데이터 볼륨
```
/data/
├── jenkins/          # Jenkins 홈 디렉토리 (중요 데이터)
│   ├── jobs/         # 작업 설정
│   ├── workspace/    # 빌드 작업공간
│   ├── plugins/      # 플러그인
│   └── users/        # 사용자 설정
├── nginx/           # Nginx 설정 (중요 데이터)
│   ├── conf.d/      # 서버 설정
│   ├── sslcert/     # SSL 인증서
│   └── htpasswd/    # 인증 파일
└── opengrok/        # OpenGrok 데이터
    ├── src/         # 소스코드
    ├── data/        # 검색 인덱스
    └── etc/         # 설정 파일
```

### 백업 전략
- **Jenkins**: `/data/jenkins` 전체 백업 필수
- **Nginx**: SSL 인증서 및 설정 파일 백업
- **OpenGrok**: 인덱스 재생성 가능하므로 소스코드만 백업

## 🔒 보안 고려사항

### 1. **SSL/TLS 암호화**
- Nginx를 통한 HTTPS 강제 적용
- Let's Encrypt 또는 사설 인증서 사용

### 2. **인증 및 권한 관리**
- LDAP 중앙 인증을 통한 통합 사용자 관리
- Jenkins 역할 기반 접근 제어
- Nginx htpasswd 기반 추가 인증

### 3. **네트워크 보안**
- 내부 네트워크를 통한 서비스 간 통신
- 외부 노출 포트 최소화

### 4. **보안 모니터링**
- Jenkins 보안 플러그인 활성화
- 정기적인 플러그인 업데이트

## 🚀 운영 가이드

### 시작 명령어
```bash
# 서비스 시작
docker compose up -d

# 로그 확인
docker compose logs -f [service_name]

# 상태 확인
docker compose ps
```

### 서비스 URL
- **Jenkins**: `https://jenkins.roboetech.com` (포트 5000)
- **OpenGrok**: `https://opengrok.roboetech.com` (포트 8081)
- **Dashboard**: `https://dashboard.roboetech.com` (포트 3000)

### 의존성 순서
1. 외부 LDAP 서버 (`172.30.1.97`) - 외부 인프라
2. `opengrok-ldap-auth` (LDAP 인증 프록시)
3. `jenkins`, `opengrok`, `jenkins-dashboard` (핵심 서비스)
4. `nginx` (프록시 - 모든 서비스 의존)

## 🔧 문제 해결 가이드

### 일반적인 문제

#### 1. **서비스 시작 실패**
```bash
# 네트워크 확인
docker network ls
docker network inspect docker_devops_bridge

# 이미지 존재 확인
docker images
```

#### 2. **볼륨 마운트 오류**
```bash
# 권한 확인
ls -la /data/
sudo chown -R 1000:1000 /data/jenkins  # Jenkins 사용자
```

#### 3. **LDAP 인증 실패**
```bash
# LDAP 인증 서비스 상태 확인
docker compose logs opengrok-ldap-auth

# 외부 LDAP 서버 연결 테스트
ldapsearch -x -H ldap://172.30.1.97:389 -b dc=roboetech,dc=com

# 인증 서비스 헬스체크
curl http://localhost:8000/health
```

#### 4. **SSL 인증서 문제**
```bash
# 인증서 확인
ls -la /data/nginx/sslcert/
openssl x509 -in /data/nginx/sslcert/cert.pem -text -noout
```

### 성능 최적화

#### 1. **Jenkins 성능 튜닝**
- JVM 힙 사이즈 조정: `JAVA_OPTS` 환경변수 수정
- 불필요한 플러그인 제거
- 빌드 히스토리 정리

#### 2. **OpenGrok 성능**
- 인덱싱 주기 조정
- 메모리 할당 최적화

## 📋 유지보수 체크리스트

### 일간
- [ ] 서비스 상태 모니터링
- [ ] 로그 확인 및 오류 검토

### 주간
- [ ] 백업 상태 확인
- [ ] 디스크 사용량 모니터링
- [ ] SSL 인증서 만료일 확인

### 월간
- [ ] Jenkins 플러그인 업데이트
- [ ] 시스템 패키지 업데이트
- [ ] 보안 패치 적용
- [ ] 성능 메트릭 검토

### 연간
- [ ] SSL 인증서 갱신
- [ ] 백업/복구 테스트
- [ ] 재해 복구 계획 검토

## 🔄 업그레이드 전략

### 서비스별 업그레이드 순서
1. **OpenGrok LDAP Auth**: 인증 프록시 - 최소 다운타임
2. **Jenkins**: 메이저 업그레이드 시 주의 (플러그인 호환성)
3. **OpenGrok**: 인덱스 재생성 필요
4. **Nginx**: 무중단 업그레이드 가능

### 백업 전 필수 작업
```bash
# 전체 서비스 중지
docker compose stop

# 데이터 백업
tar -czf backup-$(date +%Y%m%d).tar.gz /data/

# 컨테이너 백업
docker commit jenkins jenkins-backup-$(date +%Y%m%d)
```

## 📊 모니터링 및 알람

### 권장 모니터링 도구
- **Prometheus + Grafana**: 메트릭 수집 및 시각화
- **ELK Stack**: 로그 분석
- **Uptime Robot**: 외부 서비스 가용성 모니터링

### 알람 설정 대상
- 서비스 다운
- 디스크 사용량 80% 초과
- SSL 인증서 만료 30일 전
- Jenkins 빌드 실패율 증가

---

**🤖 Generated with [Claude Code](https://claude.ai/code)**

**Co-Authored-By: Claude <noreply@anthropic.com>**