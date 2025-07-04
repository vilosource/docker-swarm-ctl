interface PageTitleProps {
  title: string
  breadcrumb?: Array<{
    title: string
    href?: string
  }>
}

export default function PageTitle({ title, breadcrumb = [] }: PageTitleProps) {
  return (
    <div className="row">
      <div className="col-12">
        <div className="page-title-box">
          <div className="page-title-right">
            <ol className="breadcrumb m-0">
              <li className="breadcrumb-item">
                <a href="/">Docker Control</a>
              </li>
              {breadcrumb.map((item, index) => (
                <li 
                  key={index} 
                  className={`breadcrumb-item ${index === breadcrumb.length - 1 ? 'active' : ''}`}
                >
                  {item.href ? (
                    <a href={item.href}>{item.title}</a>
                  ) : (
                    item.title
                  )}
                </li>
              ))}
            </ol>
          </div>
          <h4 className="page-title">{title}</h4>
        </div>
      </div>
    </div>
  )
}