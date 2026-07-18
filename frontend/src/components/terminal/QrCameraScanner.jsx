import { useEffect, useId, useRef } from "react";
import { Html5Qrcode } from "html5-qrcode";

// Continuously scans with the device camera, pausing itself while onDecode
// runs (and de-duping re-triggers) so callers can just await the result of
// one scan before the next becomes possible.
export default function QrCameraScanner({ onDecode, onError, className }) {
  const readerId = "qr-reader-" + useId().replace(/[^a-zA-Z0-9]/g, "");
  const scannerRef = useRef(null);
  const onDecodeRef = useRef(onDecode);
  const busyRef = useRef(false);
  onDecodeRef.current = onDecode;

  useEffect(() => {
    const scanner = new Html5Qrcode(readerId);
    scannerRef.current = scanner;

    async function handleDecoded(text) {
      if (busyRef.current) return;
      busyRef.current = true;
      try {
        scanner.pause(true);
      } catch {
        // scanner may already be stopped/paused — safe to ignore
      }
      try {
        await onDecodeRef.current?.(text);
      } finally {
        busyRef.current = false;
        try {
          scanner.resume();
        } catch {
          // scanner may have been torn down while awaiting onDecode
        }
      }
    }

    scanner
      .start(
        { facingMode: "environment" },
        {
          fps: 10,
          qrbox: (viewfinderWidth, viewfinderHeight) => {
            const size = Math.floor(Math.min(viewfinderWidth, viewfinderHeight) * 0.7);
            return { width: size, height: size };
          },
        },
        handleDecoded,
        () => {} // per-frame "no QR found" — expected while aiming, ignored
      )
      .catch(() => {
        onError?.();
      });

    return () => {
      try {
        Promise.resolve(scanner.stop())
          .then(() => scanner.clear())
          .catch(() => {});
      } catch {
        // In StrictMode cleanup may run before camera startup has completed.
        try {
          scanner.clear();
        } catch {
          // The reader may already be cleared; nothing else to release.
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readerId]);

  return <div id={readerId} className={className} />;
}
