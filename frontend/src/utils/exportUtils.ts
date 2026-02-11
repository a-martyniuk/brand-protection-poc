import { Violation } from '../types';

export const exportToCSV = (violations: Violation[]) => {
    const headers = ["ID MeLi", "Producto", "Vendedor", "Ubicacion", "Status", "Tipo", "Precio", "MAP", "URL"];
    const rows = violations.map((v: Violation) => [
        v.meli_id,
        v.product,
        v.seller,
        v.seller_location,
        v.status,
        v.type,
        v.price,
        v.expected,
        v.url
    ]);

    const csvContent = [
        headers.join(","),
        ...rows.map((row: (string | number | boolean | undefined)[]) =>
            row.map(cell => `"${cell ?? ''}"`).join(",")
        )
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `brand_protection_report_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};
