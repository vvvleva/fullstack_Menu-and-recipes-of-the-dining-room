const { BrowserRouter, Routes, Route, NavLink } = ReactRouterDOM;

function Navigation() {
  return (
    <nav className="spa-nav">
      <NavLink to="/" end className="spa-link">
        <i className="fas fa-list"></i> Меню
      </NavLink>
      <NavLink to="/profile" className="spa-link">
        <i className="fas fa-user"></i> Профиль
      </NavLink>
      <NavLink to="/about" className="spa-link">
        <i className="fas fa-info-circle"></i> О проекте
      </NavLink>
    </nav>
  );
}

function Layout() {
  return (
    <div className="spa-card">
      <header className="spa-header">
        <div className="spa-title">
          <i className="fas fa-utensils"></i> SPA-панель столовой
        </div>
        <div className="spa-description">
          Демонстрация клиентской маршрутизации (React Router) для будущих CRUD, авторизации и интеграции с API.
        </div>
      </header>

      <Navigation />

      <main className="spa-main">
        <Routes>
          <Route path="/" element={<MenuPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/about" element={<AboutPage />} />
        </Routes>
      </main>
    </div>
  );
}

function MenuPage() {
  return (
    <section>
      <h3><i className="fas fa-list"></i> Меню на сегодня</h3>
      <p className="spa-text">
        Здесь в следующих лабораторных (ЛР №4 и №7) будут отображаться реальные данные из эндпоинтов
        <code> /api/menu </code> и <code>/api/menu/&lt;id&gt;</code> c обработкой загрузки и ошибок.
      </p>
      <ul className="spa-list">
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> Список блюд с ценой, весом и категорией</li>
        <li><i className="fas fa-exclamation-triangle" style={{color: '#ffc107'}}></i> Метка «Безопасно»/«Опасно» по результатам анализа аллергенов</li>
        <li><i className="fas fa-arrow-right" style={{color: '#667eea'}}></i> Кнопка перехода к подробной карточке блюда</li>
      </ul>
    </section>
  );
}

function ProfilePage() {
  return (
    <section>
      <h3><i className="fas fa-user"></i> Профиль и аллергены</h3>
      <p className="spa-text">
        Экран для хранения предпочтений пользователя: аллергены, диета, история выборов.
        В дальнейших ЛР (№5–6) здесь появятся авторизация и защита маршрутов.
      </p>
      <ul className="spa-list">
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> Выбор аллергенов (орехи, лактоза, глютен, морепродукты)</li>
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> Выбор диеты (веган, безглютеновая и др.)</li>
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> Сохранение настроек после входа в систему</li>
      </ul>
    </section>
  );
}

function AboutPage() {
  return (
    <section>
      <h3><i className="fas fa-info-circle"></i> О проекте</h3>
      <p className="spa-text">
        Проект "Столовая #2049" - лабораторные работы по курсу "Современные языки и системы программирования".
      </p>
      <p className="spa-text">
        Функциональность:
      </p>
      <ul className="spa-list">
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> CRUD для меню столовой</li>
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> AI-анализ аллергенов на основе нейросетевой модели</li>
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> Авторизация и аутентификация пользователей (JWT)</li>
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> Система заказов с отслеживанием статуса</li>
        <li><i className="fas fa-check-circle" style={{color: '#28a745'}}></i> Административная панель для управления</li>
      </ul>
    </section>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Layout />
    </BrowserRouter>
  );
}

const root = ReactDOM.createRoot(document.getElementById("spa-root"));
root.render(<App />);