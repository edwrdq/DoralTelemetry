import { useEffect, useState } from "react";

import MosaicView from "./components/MosaicView";
import FieldView from "./components/FieldView";
import { Settings, Thermometer, Zap } from "lucide-react";
import { RotatingContainer } from "./components/RotatingContainer";
import { useTheme, type Theme } from "./theme";
import motorImg from "./assets/proxy-image-removebg-preview.png";
export type Message = {
  version: number;
  motorCount: number;
  battery: number;
  x: number;
  y: number;
  theta: number;
  motorTemperature: number[];
  motorRpm: number[];
  motorVoltage: number[];
  ts: number; // unix time
};
const useSSE = () => {
  const [data, setData] = useState<Message | null>(null);
  useEffect(() => {
    const url = (import.meta as any).env?.VITE_SSE_URL || "http://127.0.0.1:9000/stream";
    const evtSource = new EventSource(url);

    evtSource.onmessage = (evt: MessageEvent) => {
      setData(JSON.parse(evt.data));
    };
    return () => {
      evtSource.close();
    };
  }, []);
  return data;
};
function App() {
  const data = useSSE();
  const [theme, setTheme] = useTheme();
  const [open, setOpen] = useState(false);

  return (
    <MosaicView>
      <div key="Motors">
        {Array.from({ length: data?.motorCount ?? 0 }, (_, i) => i).map((i) => (
          <div className="w-[95%] mx-auto flex bg-[var(--card-bg)] rounded-xl my-2">
            <div className="relative w-32 h-32 flex items-center justify-center">
              <img
                src={motorImg}
                className="absolute inset-0 w-full h-full object-contain"
                alt="Motor"
              />
              <span className="absolute text-xl text-white">Motor {i + 1}</span>
            </div>
            <div className="ml-auto mr-5 flex items-center my-auto gap-3">
              <Thermometer />
              <span className="font-mono text-lg">
                {data?.motorTemperature[i].toFixed(2) ?? "N/A"}ºC
              </span>
              <Zap />
              <span className="font-mono text-lg">
                {data?.motorVoltage[i].toFixed(2) ?? "N/A"} V
              </span>
              <RotatingContainer
                rpm={(data?.motorRpm[i] ?? 1) / 10}
                className="w-7 h-7"
              >
                <Settings className="w-7 h-7" />
              </RotatingContainer>
              <span className="font-mono text-lg">
                {data?.motorRpm[i].toFixed(2) ?? "N/A"} rpm
              </span>
            </div>
          </div>
        ))}
      </div>
      <div key="Position">
        <FieldView data={data} />
      </div>
      <div key="STATUS" title={`Battery @ ${(data?.battery ?? 0).toFixed(0)}%`} >
        <div className="flex items-center gap-3 relative">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            className="lucide lucide-battery-icon lucide-battery"
          >
            <path d="M 22 14 L 22 10" />
            <rect
              x="2"
              y="6"
              width={(16 * (data?.battery ?? 0)) / 100}
              height="12"
              fill="#2fcc71"
              stroke-width="0"
            />
            <rect x="2" y="6" width="16" height="12" rx="2" />
            <text
              x="10"
              y="12"
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="6"
              fill="var(--text-primary)"
              stroke="none"
              style={{ userSelect: "none", fontWeight: 400 as any }}
            >
              {(data?.battery ?? 0).toFixed(0)}%
            </text>
          </svg>
          <button
            aria-label="Open settings"
            onClick={() => setOpen((v) => !v)}
            className="p-2 rounded hover:opacity-80"
            style={{ color: "var(--settings-icon)" }}
            title="Settings"
          >
            <Settings />
          </button>
          {open && (
            <div
              className="absolute right-0 top-full mt-2 w-56 rounded-md shadow-lg z-50"
              style={{ background: "var(--card-bg)", border: "1px solid var(--topbar-border)" }}
            >
              <div className="py-2">
                {([
                  ["default", "Default"],
                  ["blue", "Blue Accents"],
                  ["gruvbox-dark", "Gruvbox Dark"],
                  ["gruvbox-light", "Gruvbox Light"],
                ] as [Theme, string][]) .map(([val, label]) => (
                  <button
                    key={val}
                    className="w-full text-left px-3 py-2 hover:opacity-90"
                    style={{ color: "var(--text-primary)" }}
                    onClick={() => {
                      setTheme(val);
                      setOpen(false);
                    }}
                  >
                    {label} {theme === val ? "✓" : ""}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </MosaicView>
  );
}

export default App;
