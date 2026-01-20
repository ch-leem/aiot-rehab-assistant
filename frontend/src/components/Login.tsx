import { useState } from "react";

type LoginProps = {
  onSubmit: (data: { nextPatientId: string; nextNurseId: string }) => void;
};

export default function Login({ onSubmit }: LoginProps) {
  const [nextPatientId, setNextPatientId] = useState("");
  const [nextNurseId, setNextNurseId] = useState("");
  const isReady = nextPatientId.trim() !== "" && nextNurseId.trim() !== "";

  return (
    <div className="login-screen enter">
      <div className="screen-label">로그인</div>
      <h1>담당 확인</h1>
      <p className="lead">
        환자 번호와 담당 의료인 번호를 입력해주세요.
      </p>
      <form
        className="login-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!isReady) return;
          onSubmit({
            nextPatientId: nextPatientId.trim(),
            nextNurseId: nextNurseId.trim(),
          });
        }}
      >
        <div className="login-box">
          <label className="field">
            <span>환자 번호</span>
            <input
              className="field-input"
              type="text"
              inputMode="numeric"
              placeholder="예시"
              value={nextPatientId}
              onChange={(event) => setNextPatientId(event.target.value)}
            />
          </label>
          <label className="field">
            <span>의료인 번호</span>
            <input
              className="field-input"
              type="text"
              inputMode="numeric"
              placeholder="예시"
              value={nextNurseId}
              onChange={(event) => setNextNurseId(event.target.value)}
            />
          </label>
        </div>
        <div className="cta-row">
          <button className="primary-button" type="submit" disabled={!isReady}>
            확인하고 시작
          </button>
          <button className="ghost-button" type="button">
            입력 도움말
          </button>
        </div>
      </form>
    </div>
  );
}
