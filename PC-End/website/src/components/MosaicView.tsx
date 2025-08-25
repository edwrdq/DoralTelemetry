import React, { useMemo, useState } from "react";
import {
  Mosaic,
  MosaicWindow,
  type MosaicNode,
  createBalancedTreeFromLeaves,
} from "react-mosaic-component";
import "react-mosaic-component/react-mosaic-component.css";

type MosaicViewProps = {
  children: React.ReactElement<{ key: string }>[];
};

function getKey(child: React.ReactElement): string {
  // React keys are always strings, but TS types can be string | number | null
  // We enforce string for window ids
  if (typeof child.key === "string") return child.key;
  if (typeof child.key === "number") return String(child.key);
  throw new Error("Each child must have a unique string or number key");
}

export const MosaicView: React.FC<MosaicViewProps> = ({ children: childrenReal }) => {
  const children = childrenReal.filter(c => c.key !== "STATUS");
  // Extract keys and map to children
  const allKeys = useMemo(() => children.map(getKey), [children]);
  const childMap = useMemo(
    () =>
      Object.fromEntries(children.map((child) => [getKey(child), child])),
    [children]
  );

  // Settings state: which windows are visible
  const [visibleKeys, setVisibleKeys] = useState<string[]>(allKeys);

  // Mosaic tree state
  const [mosaicTree, setMosaicTree] = useState<MosaicNode<string> | null>(() =>
    createBalancedTreeFromLeaves(allKeys)
  );

  // Track previous visible keys to detect actual changes
  const prevVisibleKeysRef = React.useRef<string[]>(allKeys);

  // When visibleKeys changes (keys added/removed), update the mosaic tree
  React.useEffect(() => {
    const prevKeys = prevVisibleKeysRef.current;
    const currentKeys = visibleKeys;

    // Only recreate tree if the set of keys actually changed
    const keysChanged =
      prevKeys.length !== currentKeys.length ||
      prevKeys.some(key => !currentKeys.includes(key)) ||
      currentKeys.some(key => !prevKeys.includes(key));

    if (keysChanged) {
      setMosaicTree(
        visibleKeys.length > 0 ? createBalancedTreeFromLeaves(visibleKeys) : null
      );
    }

    prevVisibleKeysRef.current = visibleKeys;
  }, [visibleKeys]);

  // When allKeys changes (children change), update visibleKeys and tree
  React.useEffect(() => {
    setVisibleKeys((prev) =>
      prev.filter((k) => allKeys.includes(k)).length > 0
        ? prev.filter((k) => allKeys.includes(k))
        : allKeys
    );
  }, [allKeys]);

  // Settings panel: toggles for each child
  const SettingsPanel = (
    <div
      className="flex items-center gap-6 p-2 h-[5%]"
      style={{
        backgroundColor: "var(--topbar-bg)",
        borderBottom: "1px solid var(--topbar-border)",
      }}
    >
      {allKeys.map((key) => (
        <label key={key} style={{ display: "flex", alignItems: "center" }}>
          <input
            type="checkbox"
            checked={visibleKeys.includes(key)}
            onChange={() =>
              setVisibleKeys((prev) =>
                prev.includes(key)
                  ? prev.filter((k) => k !== key)
                  : [...prev, key]
              )
            }
            style={{ marginRight: 4 }}
          />
          {key}
        </label>
      ))}
      <div className="w-full" />
      {childrenReal.filter(c => c.key === "STATUS")}
    </div>
  );

  return (
    <div className="w-screen h-screen" style={{ background: "var(--app-bg)", color: "var(--text-primary)" }}>
      {SettingsPanel}
      <div className="w-full h-[95%]">
        <Mosaic<string>
          renderTile={(id, path) => (
            <MosaicWindow<string> title={id} path={path}>
              {childMap[id]}
            </MosaicWindow>
          )}
          value={mosaicTree}
          onChange={setMosaicTree}
          className="mosaic-blueprint-theme"
        />
        {visibleKeys.length === 0 && (
          <div
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: "4rem",
              textAlign: "center",
              color: "#888",
            }}
          >
            No windows selected.
          </div>
        )}
      </div>
    </div>
  );
};

export default MosaicView;
