import clsx from "clsx";
import { Crown, Trophy } from "lucide-react";
import { Card, CardBody, CardHeader } from "../ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td } from "../ui/Table";
import Badge from "../ui/Badge";
import { EmptyState } from "../ui/Misc";

const RANK_ICON = { 0: Crown, 1: Trophy, 2: Trophy };
const RANK_TONE = { 0: "text-brass-500", 1: "text-bark-200", 2: "text-wood-700" };
const AVATAR_COLORS = [
  "bg-brass-600",
  "bg-forest-600",
  "bg-wood-600",
  "bg-olive-600",
  "bg-bark-700",
  "bg-status-blue",
];

function initials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
}

function avatarColor(seed) {
  let hash = 0;
  for (const ch of seed) hash = (hash * 31 + ch.charCodeAt(0)) % AVATAR_COLORS.length;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export default function TopPerformers({ rows }) {
  return (
    <Card>
      <CardHeader title="Eng faol xodimlar" subtitle="Live performance ranking" />
      <CardBody className="p-0">
        {rows.length === 0 ? (
          <EmptyState title="Ma'lumot yo'q" />
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th>O'rin</Th>
                <Th>Xodim</Th>
                <Th>Ishlab chiqarish</Th>
                <Th>Stanoklar</Th>
                <Th>Samaradorlik</Th>
              </tr>
            </Thead>
            <Tbody>
              {rows.map((row, i) => {
                const Icon = RANK_ICON[i];
                return (
                  <Tr key={row.employee_id} className={i === 0 ? "bg-[var(--accent-soft)]" : undefined}>
                    <Td>{Icon ? <Icon size={16} className={RANK_TONE[i]} /> : <span className="text-xs font-semibold text-[var(--ink-faint)]">#{i + 1}</span>}</Td>
                    <Td>
                      <div className="flex items-center gap-2.5">
                        <span className={clsx("flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white", avatarColor(row.name))}>
                          {initials(row.name)}
                        </span>
                        <div>
                          <p className="font-medium">{row.name}</p>
                          {i === 0 && <span className="text-[10px] font-bold uppercase text-[var(--accent-strong)]">Chempion</span>}
                        </div>
                      </div>
                    </Td>
                    <Td>
                      <span className="font-semibold">{row.output}</span>{" "}
                      <span className="text-xs text-[var(--ink-soft)]">dona</span>
                    </Td>
                    <Td>
                      <Badge tone="gray">{row.machines} ta stanok</Badge>
                    </Td>
                    <Td>
                      <div className="flex min-w-[120px] items-center gap-2">
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--surface-muted)]">
                          <div className="h-full rounded-full bg-[linear-gradient(90deg,var(--accent),var(--accent-2))]" style={{ width: `${Math.min(row.efficiency ?? 0, 100)}%` }} />
                        </div>
                        <span className="w-10 text-right text-xs font-semibold">{row.efficiency !== null ? `${row.efficiency}%` : "—"}</span>
                      </div>
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        )}
      </CardBody>
    </Card>
  );
}
