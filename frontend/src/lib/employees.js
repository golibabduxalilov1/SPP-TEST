export function departmentLabel(employee) {
  if (employee.role === "operator") return employee.department_name || "—";
  if (employee.role === "manager") {
    const names = (employee.managed_departments_detail || []).map((t) => t.name);
    return names.length ? names.join(", ") : "—";
  }
  return "—";
}
