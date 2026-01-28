import { useState } from "react";

type LoginProps = {
  onSubmit: (data: { nextPatientId: string; nextNurseId: string }) => void;
  isLoading?: boolean;
  errorMessage?: string;
};

export default function Login({ onSubmit, isLoading = false, errorMessage }: LoginProps) {
  const [nextPatientId, setNextPatientId] = useState("");
  const [nextNurseId, setNextNurseId] = useState("");
  const isReady = nextPatientId.trim() !== "" && nextNurseId.trim() !== "";

  return (
    <div className="login-screen enter">
      <div className="screen-label">로그인</div>
      <h1>담당 확인</h1>
      <div className="login-center">
        <p className="lead">
          환자 번호와 담당 의료인 번호를 입력해주세요.
        </p>
        <form
          className="login-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!isReady || isLoading) return;
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
          <div className="cta-row login-cta">
            <button className="primary-button" type="submit" disabled={!isReady || isLoading}>
              확인하고 시작
            </button>
          </div>
          {errorMessage && <div className="login-error">{errorMessage}</div>}
        </form>
      </div>
    </div>
  );
}
