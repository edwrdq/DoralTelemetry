import { useEffect, useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import "./App.css";

type Message = {
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
    const evtSource = new EventSource("http://localhost:34453/stream");

    evtSource.onmessage = (evt: MessageEvent) => {
      setData(JSON.parse(evt.data))
    };
  });
  return data;
}
function App() {
  const data = useSSE();

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  );
}

export default App;
