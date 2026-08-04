import { useRef, useState } from "react";
import { format } from "date-fns";
import html2canvas from "html2canvas-pro";
import { QRCodeCanvas } from "qrcode.react";
import { CalendarCheck, Check, Download, Printer, RotateCw, TreePine, User as UserIcon } from "lucide-react";
import Button from "../ui/Button";
import { departmentLabel } from "../../lib/employees";
import "./EmployeeBadge.css";

const FACTORY_NAME = "MEBEL ZAVODI";

// html2canvas can't rasterize a live <canvas> via cloneNode (clones come back
// blank), so the QR canvas on the back side has to be swapped for a still
// image of its current pixels before the offscreen wrapper is captured.
function replaceCanvasesWithImages(original, clone) {
  const originals = original.querySelectorAll("canvas");
  const clones = clone.querySelectorAll("canvas");
  originals.forEach((originalCanvas, i) => {
    const cloneCanvas = clones[i];
    if (!cloneCanvas) return;
    const rect = originalCanvas.getBoundingClientRect();
    const img = document.createElement("img");
    img.src = originalCanvas.toDataURL("image/png");
    img.style.width = `${rect.width}px`;
    img.style.height = `${rect.height}px`;
    cloneCanvas.replaceWith(img);
  });
}

export default function EmployeeBadge({ employee }) {
  const [flipped, setFlipped] = useState(false);
  const frontRef = useRef(null);
  const backRef = useRef(null);

  if (!employee) return null;

  const fullName = [employee.first_name, employee.last_name].filter(Boolean).join(" ") || employee.username;
  const roleLabel = employee.specialization_display || employee.role_display;
  const department = departmentLabel(employee);
  const issueDate = employee.date_joined ? format(new Date(employee.date_joined), "dd.MM.yyyy") : "—";

  // Captures front + back side by side into a single canvas — shared by the
  // PNG download and the print flow (which prints an isolated window
  // containing just this image, matching the QR-print pattern used
  // elsewhere in this app rather than printing the whole admin page).
  async function captureBadge() {
    const front = frontRef.current;
    const back = backRef.current;
    if (!front || !back) return null;

    const wrapper = document.createElement("div");
    wrapper.style.position = "fixed";
    wrapper.style.left = "-9999px";
    wrapper.style.top = "-9999px";
    wrapper.style.display = "flex";
    wrapper.style.gap = "24px";
    wrapper.style.padding = "24px";
    wrapper.style.backgroundColor = "#0f172a";
    wrapper.style.borderRadius = "24px";

    const frontClone = front.cloneNode(true);
    const backClone = back.cloneNode(true);
    replaceCanvasesWithImages(back, backClone);
    for (const clone of [frontClone, backClone]) {
      clone.style.position = "relative";
      clone.style.transform = "none";
      clone.style.webkitBackfaceVisibility = "visible";
      clone.style.backfaceVisibility = "visible";
      // Both faces carry a class-based `visibility` rule that only resolves
      // to "visible" inside the live .employee-badge-card-flipped context —
      // outside it (as in this offscreen wrapper), the back face's base rule
      // would otherwise render it invisible regardless of the current flip
      // state. The export always wants both faces shown.
      clone.style.visibility = "visible";
      clone.style.width = "340px";
      clone.style.height = "520px";
      clone.style.top = "0";
      clone.style.left = "0";
    }
    wrapper.appendChild(frontClone);
    wrapper.appendChild(backClone);
    document.body.appendChild(wrapper);

    try {
      return await html2canvas(wrapper, { scale: 3, useCORS: true, backgroundColor: "#0f172a" });
    } finally {
      document.body.removeChild(wrapper);
    }
  }

  async function downloadPNG() {
    const canvas = await captureBadge();
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `Beyjik_${fullName.replace(/\s+/g, "_")}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  async function printBadge() {
    const canvas = await captureBadge();
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    const win = window.open("", "_blank", "width=760,height=560");
    if (!win) return;
    win.document.write(
      `<title>Beyjik — ${fullName}</title>` +
        `<body style="display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">` +
        `<img src="${dataUrl}" style="max-width:100%;height:auto;" onload="window.print()" />` +
        `</body>`
    );
    win.document.close();
  }

  return (
    <div className="employee-badge flex flex-col items-center">
      <div className="mb-4 flex flex-wrap items-center justify-center gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={() => setFlipped((f) => !f)}>
          <RotateCw size={14} /> {flipped ? "Old tarafini ko'rish" : "Orqa tarafini ko'rish"}
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={downloadPNG}>
          <Download size={14} /> PNG saqlash
        </Button>
        <Button type="button" size="sm" onClick={printBadge}>
          <Printer size={14} /> Chop etish
        </Button>
      </div>

      <div className="flex flex-col items-center -mb-3">
        <div className="employee-badge-lanyard-strap relative flex h-14 w-14 items-center justify-center rounded-t-md shadow-lg">
          <div className="h-full w-3.5 bg-slate-950/40" />
          <span className="absolute rotate-90 whitespace-nowrap text-[8px] font-extrabold uppercase tracking-widest text-slate-400">
            MEBEL FABRIKA
          </span>
        </div>
        <div className="employee-badge-clip-metallic flex h-4 w-9 items-center justify-center rounded-b-md border border-slate-400/50 shadow-md">
          <div className="h-1.5 w-4 rounded-full bg-slate-900" />
        </div>
        <div className="-mt-1 h-6 w-6 rounded-full border-2 border-slate-400 bg-transparent shadow-md" />
      </div>

      <div className="employee-badge-perspective h-130 w-85">
        <div className={`employee-badge-card-inner ${flipped ? "employee-badge-card-flipped" : ""}`}>
          {/* FRONT */}
          <div ref={frontRef} className="employee-badge-card-front">
            <div className="employee-badge-wood flex h-full w-full flex-col justify-between overflow-hidden rounded-2xl border-4 border-slate-800 text-white shadow-2xl">
              <div className="z-10 flex w-full justify-center pt-2">
                <div className="h-2.5 w-12 rounded-full border border-slate-700 bg-slate-950/90 shadow-inner" />
              </div>

              <div className="flex flex-col items-center justify-center border-b border-amber-600/30 bg-linear-to-r from-amber-950 via-amber-900 to-amber-950 px-4 py-2 text-center">
                <div className="flex items-center justify-center gap-2">
                  <TreePine size={14} className="text-amber-400" />
                  <h3 className="employee-badge-brand text-base font-bold uppercase leading-tight tracking-wider text-amber-100">
                    {FACTORY_NAME}
                  </h3>
                </div>
                <span className="mt-0.5 block text-[8.5px] font-extrabold uppercase tracking-widest text-amber-400">
                  SIFAT &bull; ISHONCH &bull; MAS'ULIYAT
                </span>
              </div>

              <div className="z-10 flex flex-1 flex-col items-center justify-between px-5 py-3 text-center">
                <div className="relative my-1.5">
                  <div className="absolute -right-1.5 -top-1.5 z-20 flex h-5 w-5 items-center justify-center rounded-full border border-white/60 bg-linear-to-br from-amber-400 to-amber-600 text-[10px] font-bold text-slate-950 shadow-lg">
                    <Check size={11} strokeWidth={3} />
                  </div>
                  <div className="h-40 w-32 rounded-xl bg-linear-to-b from-amber-500 via-amber-700 to-amber-900 p-1 shadow-xl">
                    <div className="flex h-full w-full items-center justify-center overflow-hidden rounded-lg bg-slate-900">
                      {employee.photo ? (
                        <img
                          src={employee.photo}
                          alt={fullName}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <UserIcon size={56} className="text-slate-600" />
                      )}
                    </div>
                  </div>
                </div>

                <div className="my-1 w-full space-y-1">
                  <h2 className="text-xl font-extrabold uppercase leading-tight tracking-wide text-white drop-shadow">
                    {fullName}
                  </h2>
                  <div className="inline-block rounded-full border border-amber-400/40 bg-amber-500/20 px-3.5 py-0.5">
                    <span className="text-xs font-bold uppercase tracking-wide text-amber-300">{roleLabel}</span>
                  </div>
                </div>

                <div className="my-1 w-full rounded-xl border border-slate-700/60 bg-slate-950/80 px-3 py-1.5">
                  <span className="block text-[9px] font-medium uppercase tracking-wider text-slate-400">Bo'lim:</span>
                  <span className="block text-xs font-bold text-slate-200">{department}</span>
                </div>

                <div className="flex w-full items-center justify-center border-t border-slate-700/60 pt-2 text-center">
                  <div className="flex items-center justify-center gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-1.5">
                    <CalendarCheck size={12} className="text-amber-400" />
                    <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">BERILGAN VAQTI:</span>
                    <span className="font-mono text-xs font-bold tracking-wide text-amber-200">{issueDate}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-center border-t border-slate-800 bg-slate-950 px-2 py-2 text-center text-[9px] font-extrabold tracking-wider text-amber-400">
                <span>BIRGALIKDA YARATAMIZ, SIFAT BILAN ISHLAYMIZ!</span>
              </div>
            </div>
          </div>

          {/* BACK */}
          <div ref={backRef} className="employee-badge-card-back">
            <div className="employee-badge-wood flex h-full w-full flex-col justify-between overflow-hidden rounded-2xl border-4 border-slate-800 p-5 text-center text-white shadow-2xl">
              <div className="flex w-full justify-center">
                <div className="h-2.5 w-12 rounded-full border border-slate-700 bg-slate-950/90 shadow-inner" />
              </div>

              <div className="border-b border-amber-600/30 pb-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-amber-300">NAZORAT VA SKANERLASH</h4>
                <p className="text-[9px] text-slate-400">Turniket va nazorat punktlari uchun QR-kod</p>
              </div>

              <div className="my-auto flex flex-col items-center justify-center">
                <div className="rounded-2xl border-4 border-amber-500 bg-white p-3 shadow-2xl">
                  <QRCodeCanvas value={employee.badge_token || ""} size={192} level="M" />
                </div>
                <span className="mt-3 text-xs font-mono font-bold uppercase tracking-widest text-amber-400">
                  SKANERLASH UCHUN
                </span>
              </div>

              <div className="space-y-1 rounded-xl border border-slate-800 bg-slate-950/90 p-2.5 text-left text-[9px] text-slate-400">
                <p className="text-[10px] font-semibold uppercase text-amber-400">Qoidalar:</p>
                <p>1. Beydjik zavod hududida doim ko'krakda taqilishi shart.</p>
                <p>2. Begona shaxslarga berish qat'iyan man etiladi.</p>
              </div>

              <div className="border-t border-slate-800 pt-1 text-[8px] uppercase tracking-widest text-slate-500">
                RASMIY ID CARD &bull; MEBEL FABRIKASI
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
