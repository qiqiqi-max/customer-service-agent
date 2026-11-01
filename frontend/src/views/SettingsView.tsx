import { Activity, Bot, KeyRound, Search, Settings, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { clearCredentials, loadCredentials, saveCredentials } from "../api/credentials";

export function SettingsView(props: { onCredentialsChange: (message: string) => void }) {
  const [apiKey, setApiKey] = useState(() => loadCredentials().apiKey);
  const [approverKey, setApproverKey] = useState(() => loadCredentials().approverKey);

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveCredentials({ apiKey, approverKey });
    props.onCredentialsChange("访问密钥已保存，仅在当前标签页有效");
  }

  function handleClear() {
    clearCredentials();
    setApiKey("");
    setApproverKey("");
    props.onCredentialsChange("访问密钥已清除");
  }

  return (
    <div className="page is-narrow">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>访问密钥</h2>
            <p>后端开启 API_KEYS 鉴权后需要填写</p>
          </div>
          <KeyRound size={18} />
        </div>
        <form className="panel-body form-stack" onSubmit={handleSave}>
          <label className="field">
            <span>API 密钥（API_KEYS）</span>
            <input
              autoComplete="off"
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="后端未配置 API_KEYS 时可留空"
              type="password"
              value={apiKey}
            />
          </label>
          <label className="field">
            <span>退款审批人密钥（REFUND_APPROVER_KEYS）</span>
            <input
              autoComplete="off"
              onChange={(event) => setApproverKey(event.target.value)}
              placeholder="只有审批人需要填写，用于批准、拒绝和执行退款"
              type="password"
              value={approverKey}
            />
          </label>
          <p className="form-hint">
            密钥只保存在当前标签页的 sessionStorage 中，关闭标签页后需要重新填写。
          </p>
          <div className="form-actions">
            <button className="btn" onClick={handleClear} type="button">清除</button>
            <button className="btn primary" type="submit">保存</button>
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>接入配置</h2>
            <p>这些配置在后端 .env.local 中修改</p>
          </div>
          <Settings size={18} />
        </div>
        <div className="config-list">
          <ConfigRow
            icon={Bot}
            title="大模型"
            value="DeepSeek / 智谱 / 火山引擎"
            note="通过后端 .env.local 的 LLM_PROVIDER 与 API Key 切换。"
          />
          <ConfigRow
            icon={Search}
            title="知识库"
            value="Dify Dataset"
            note="商品知识和 FAQ 分别使用 DIFY_DATASET_ID 与 DIFY_FAQ_DATASET_ID。"
          />
          <ConfigRow
            icon={Activity}
            title="业务系统"
            value="本地模拟 / HTTP 适配器"
            note="订单、物流、退款走 BUSINESS_DATA_PROVIDER。"
          />
          <ConfigRow
            icon={ShieldCheck}
            title="API 鉴权"
            value="X-API-Key"
            note="后端配置 API_KEYS 后，在上方填写访问密钥；退款审批另需 REFUND_APPROVER_KEYS 中的密钥。"
          />
        </div>
      </section>
    </div>
  );
}

function ConfigRow(props: {
  icon: typeof Bot;
  note: string;
  title: string;
  value: string;
}) {
  const Icon = props.icon;
  return (
    <article className="config-row">
      <Icon size={20} />
      <div>
        <strong>{props.title}</strong>
        <span>{props.value}</span>
        <p>{props.note}</p>
      </div>
    </article>
  );
}
