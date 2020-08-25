import React, { useRef, useEffect } from "react";

function useIsFirstRender() {
  const isRenderRef = useRef(true);
  useEffect(() => {
    isRenderRef.current = false;
  }, []);
  return isRenderRef.current;
}

export default useIsFirstRender;
