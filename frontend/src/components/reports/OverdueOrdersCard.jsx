import { format } from "date-fns";
import { Card, CardHeader, CardBody } from "../ui/Card";
import { Table, Thead, Tbody, Th, Tr, Td, EmptyRow } from "../ui/Table";
import Badge from "../ui/Badge";
import { EmptyState } from "../ui/Misc";

export default function OverdueOrdersCard({ orders }) {
  return (
    <Card>
      <CardHeader title="Kechikkan buyurtmalar" subtitle="Muddati o'tgan, lekin hali yakunlanmagan buyurtmalar" />
      <CardBody className="p-0">
        {orders.length === 0 ? (
          <EmptyState title="Kechikkan buyurtma yo'q" subtitle="Barcha buyurtmalar belgilangan muddatda." />
        ) : (
          <Table>
            <Thead>
              <tr>
                <Th>Buyurtma</Th>
                <Th>Mijoz</Th>
                <Th>Muddat</Th>
                <Th>Kechikish</Th>
                <Th>Status</Th>
              </tr>
            </Thead>
            <Tbody>
              {orders.length === 0 && <EmptyRow colSpan={5} />}
              {orders.map((o) => (
                <Tr key={o.id}>
                  <Td className="font-medium">#{o.order_no}</Td>
                  <Td>{o.customer_name}</Td>
                  <Td>{format(new Date(o.deadline), "dd.MM.yyyy")}</Td>
                  <Td>
                    <Badge tone="red">{o.days_overdue} kun</Badge>
                  </Td>
                  <Td>{o.status_label}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </CardBody>
    </Card>
  );
}
