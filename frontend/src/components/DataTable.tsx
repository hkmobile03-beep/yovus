interface Column<T> {
  key: string
  title: string
  render?: (row: T) => React.ReactNode
  align?: 'left' | 'right' | 'center'
  width?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  emptyText?: string
}

export default function DataTable<T extends Record<string, any>>({
  columns,
  data,
  emptyText = '暂无数据',
}: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border">
            {columns.map(col => (
              <th
                key={col.key}
                className={`px-4 py-3 text-xs font-normal text-ink-muted tracking-wider text-${col.align || 'left'} ${col.width || ''}`}
              >
                {col.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-ink-muted text-sm">
                {emptyText}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr key={i} className="border-b border-border-light hover:bg-paper-warm/50 transition-colors">
                {columns.map(col => (
                  <td
                    key={col.key}
                    className={`px-4 py-3 text-sm text-${col.align || 'left'}`}
                  >
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
