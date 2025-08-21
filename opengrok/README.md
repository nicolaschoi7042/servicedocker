# OpenGrok LDAP Authentication Service

이 디렉토리는 OpenGrok 코드 검색 플랫폼의 LDAP 인증 시스템을 포함합니다.

## 📁 파일 구조

```
opengrok/
├── README.md                    # 이 파일
├── ldap-auth-service.py         # 기본 LDAP 인증 서비스 (v1)
├── ldap-auth-service-v2.py      # 향상된 웹 로그인 서비스 (v2)
├── Dockerfile                   # Docker 이미지 빌드 파일
└── requirements.txt             # Python 의존성 패키지
```

## 🚀 기능

### v2 (현재 버전) - Web-based Login
- **웹 기반 로그인 페이지**: Basic Auth 팝업 대신 아름다운 로그인 인터페이스
- **12시간 세션 관리**: JWT 토큰 기반 자동 세션 타임아웃
- **한국어 사용자 인터페이스**: 직관적인 로그인 안내
- **반응형 디자인**: 모바일/데스크톱 지원
- **보안 강화**: HTTPS 전용 쿠키, HttpOnly 설정

### v1 (레거시) - Basic Auth
- HTTP Basic Authentication 지원
- LDAP 서버 연동
- 한글 문자 처리 개선

## 🔧 빌드 & 배포

### Docker 이미지 빌드
```bash
cd opengrok
docker build -t opengrok-ldap-auth:v2 .
```

### 환경 변수
- `LDAP_SERVER`: LDAP 서버 주소 (기본값: ldap://openldap:389)
- `LDAP_USER_BASE`: 사용자 검색 기준 DN (기본값: ou=users,dc=roboetech,dc=com)
- `LDAP_BIND_DN`: LDAP 바인딩 계정 DN (기본값: cn=admin,dc=roboetech,dc=com)
- `LDAP_BIND_PASSWORD`: LDAP 바인딩 계정 비밀번호 (기본값: admin)
- `JWT_SECRET`: JWT 토큰 암호화 시크릿

## 🌐 엔드포인트

- `/login` - 웹 로그인 페이지
- `/logout` - 로그아웃
- `/auth` - Nginx auth_request 엔드포인트
- `/health` - 헬스 체크
- `/validate` - 직접 인증 검증 (API)

## 🔐 사용법

### 로그인 정보
- **사용자 ID**: 본인의 이메일 ID
- **초기 비밀번호**: Gerrit 로그인 암호

### 접속 URL
- **OpenGrok 메인**: https://opengrok.roboetech.com
- **직접 로그인**: https://opengrok.roboetech.com/login

## 🛠️ 개발

### 로컬 실행
```bash
cd opengrok
pip install -r requirements.txt
python ldap-auth-service-v2.py
```

### 테스트
```bash
# 헬스 체크
curl http://localhost:8000/health

# 로그인 페이지
curl http://localhost:8000/login
```

## 📝 변경 이력

- **v2.0**: 웹 기반 로그인 시스템 구현
- **v1.1**: 한글 문자 처리 개선
- **v1.0**: 기본 Basic Auth 구현