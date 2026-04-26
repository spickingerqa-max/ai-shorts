<?php
$host = getenv('MYSQL_HOST')     ?: 'mysql';
$user = getenv('MYSQL_USER')     ?: 'shorts';
$pass = getenv('MYSQL_PASSWORD') ?: '';
$db   = getenv('MYSQL_DATABASE') ?: 'shortsdb';

$conn = @mysqli_connect($host, $user, $pass, $db);
$db_ok = (bool)$conn;

// 언어 추출: filename에서 "genre_lang_timestamp.mp4" 파싱
function extract_lang($filename) {
    $parts = explode('_', basename($filename, '.mp4'));
    return (count($parts) >= 2 && in_array($parts[1], ['ko','en'])) ? $parts[1] : 'ko';
}

function lang_label($lang) {
    return $lang === 'en' ? '🇺🇸 EN' : '🇰🇷 KO';
}

// 필터
$genre_filter = $_GET['genre'] ?? 'all';
$lang_filter  = $_GET['lang']  ?? 'all';
$valid_genres = ['all','horror','history','success','trend'];
$valid_langs  = ['all','ko','en'];
if (!in_array($genre_filter, $valid_genres)) $genre_filter = 'all';
if (!in_array($lang_filter,  $valid_langs))  $lang_filter  = 'all';

// 통계
$stats = ['total'=>0,'horror'=>0,'history'=>0,'success'=>0,'trend'=>0,'ko'=>0,'en'=>0];
$videos = [];

if ($db_ok) {
    $res = mysqli_query($conn, "SELECT * FROM shorts ORDER BY id DESC");
    while ($row = mysqli_fetch_assoc($res)) {
        $lang = extract_lang($row['filename']);
        $row['lang'] = $lang;
        $stats['total']++;
        if (isset($stats[$row['genre']])) $stats[$row['genre']]++;
        if (isset($stats[$lang])) $stats[$lang]++;
        $videos[] = $row;
    }
}

// 필터 적용
$filtered = array_filter($videos, function($v) use ($genre_filter, $lang_filter) {
    $g = ($genre_filter === 'all' || $v['genre'] === $genre_filter);
    $l = ($lang_filter  === 'all' || $v['lang']  === $lang_filter);
    return $g && $l;
});

$genre_icons = ['horror'=>'👻','history'=>'📜','success'=>'🚀','trend'=>'🔥'];
$genre_colors = ['horror'=>'#e74c3c','history'=>'#3498db','success'=>'#2ecc71','trend'=>'#f39c12'];
?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Shorts Factory</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d0d0d; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; min-height: 100vh; }

  header { background: #161616; border-bottom: 1px solid #2a2a2a; padding: 18px 24px;
           display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
  header h1 { font-size: 1.4rem; font-weight: 700; color: #fff; letter-spacing: 1px; }
  .live-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
              background: #2ecc71; margin-right: 6px; animation: blink 1.2s infinite; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

  .stats-row { display: flex; flex-wrap: wrap; gap: 12px; padding: 20px 24px; }
  .stat-card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px;
               padding: 14px 20px; flex: 1; min-width: 120px; text-align: center; }
  .stat-card .num  { font-size: 2rem; font-weight: 700; }
  .stat-card .label{ font-size: 0.75rem; color: #888; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }
  .stat-card.total .num  { color: #fff; }
  .stat-card.horror .num { color: #e74c3c; }
  .stat-card.history .num{ color: #3498db; }
  .stat-card.success .num{ color: #2ecc71; }
  .stat-card.trend .num  { color: #f39c12; }
  .stat-card.ko .num     { color: #a29bfe; }
  .stat-card.en .num     { color: #74b9ff; }

  .filters { padding: 0 24px 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .filter-group { display: flex; flex-wrap: wrap; gap: 6px; }
  .filter-sep { color: #444; margin: 0 6px; }
  .btn { padding: 7px 16px; border-radius: 20px; border: 1px solid #333; background: #1a1a1a;
         color: #aaa; font-size: 0.82rem; cursor: pointer; text-decoration: none;
         transition: all .15s; white-space: nowrap; }
  .btn:hover { border-color: #555; color: #fff; }
  .btn.active { background: #fff; color: #000; border-color: #fff; font-weight: 600; }
  .btn.horror  { border-color: #e74c3c; color: #e74c3c; }
  .btn.horror.active  { background: #e74c3c; color: #fff; }
  .btn.history { border-color: #3498db; color: #3498db; }
  .btn.history.active { background: #3498db; color: #fff; }
  .btn.success { border-color: #2ecc71; color: #2ecc71; }
  .btn.success.active { background: #2ecc71; color: #000; }
  .btn.trend   { border-color: #f39c12; color: #f39c12; }
  .btn.trend.active   { background: #f39c12; color: #000; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px; padding: 0 24px 40px; }
  .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px;
          overflow: hidden; transition: transform .2s, border-color .2s; }
  .card:hover { transform: translateY(-2px); border-color: #444; }

  .card-video { width: 100%; aspect-ratio: 9/16; background: #000; display: block; }
  .card-body { padding: 14px 16px; }
  .card-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
  .badge { font-size: 0.72rem; padding: 3px 9px; border-radius: 12px; font-weight: 600; }
  .badge-genre { color: #fff; }
  .badge-lang  { background: #2a2a2a; color: #aaa; }
  .card-title { font-size: 0.95rem; font-weight: 600; color: #fff; margin-bottom: 6px;
                line-height: 1.4; word-break: break-word; }
  .card-info  { font-size: 0.75rem; color: #666; display: flex; justify-content: space-between; }

  .no-data { grid-column: 1/-1; text-align: center; padding: 60px 20px; color: #555; }
  .no-data .icon { font-size: 3rem; margin-bottom: 12px; }

  .db-error { background: #2c1a1a; border: 1px solid #e74c3c33; border-radius: 10px;
              margin: 20px 24px; padding: 16px 20px; color: #e74c3c; font-size: 0.9rem; }

  @media (max-width: 600px) {
    .stats-row { gap: 8px; padding: 14px 14px; }
    .grid { padding: 0 14px 30px; gap: 12px; }
    .filters { padding: 0 14px 12px; }
  }
</style>
</head>
<body>

<header>
  <h1><span class="live-dot"></span>Shorts Factory</h1>
  <span style="font-size:.8rem;color:#555;">5초마다 자동 갱신</span>
</header>

<?php if (!$db_ok): ?>
<div class="db-error">⚠️ MySQL 연결 실패 — 컨테이너 기동 중이거나 설정을 확인하세요.</div>
<?php endif; ?>

<!-- 통계 -->
<div class="stats-row">
  <div class="stat-card total">
    <div class="num"><?= $stats['total'] ?></div>
    <div class="label">Total</div>
  </div>
  <?php foreach (['horror','history','success','trend'] as $g): ?>
  <div class="stat-card <?= $g ?>">
    <div class="num"><?= $stats[$g] ?></div>
    <div class="label"><?= $genre_icons[$g] ?> <?= $g ?></div>
  </div>
  <?php endforeach; ?>
  <div class="stat-card ko">
    <div class="num"><?= $stats['ko'] ?></div>
    <div class="label">🇰🇷 KO</div>
  </div>
  <div class="stat-card en">
    <div class="num"><?= $stats['en'] ?></div>
    <div class="label">🇺🇸 EN</div>
  </div>
</div>

<!-- 필터 -->
<div class="filters">
  <div class="filter-group">
    <?php
    $genres_list = ['all'=>'전체', 'horror'=>'👻 Horror', 'history'=>'📜 History',
                    'success'=>'🚀 Success', 'trend'=>'🔥 Trend'];
    foreach ($genres_list as $key => $label):
      $active = ($genre_filter === $key) ? 'active' : '';
      $url = '?genre='.$key.'&lang='.$lang_filter;
    ?>
    <a href="<?= $url ?>" class="btn <?= $key === 'all' ? '' : $key ?> <?= $active ?>"><?= $label ?></a>
    <?php endforeach; ?>
  </div>
  <span class="filter-sep">|</span>
  <div class="filter-group">
    <?php
    $langs_list = ['all'=>'전체', 'ko'=>'🇰🇷 KO', 'en'=>'🇺🇸 EN'];
    foreach ($langs_list as $key => $label):
      $active = ($lang_filter === $key) ? 'active' : '';
      $url = '?genre='.$genre_filter.'&lang='.$key;
    ?>
    <a href="<?= $url ?>" class="btn <?= $active ?>"><?= $label ?></a>
    <?php endforeach; ?>
  </div>
</div>

<!-- 영상 목록 -->
<div class="grid">
<?php if (empty($filtered)): ?>
  <div class="no-data">
    <div class="icon">🎬</div>
    <div>아직 생성된 영상이 없습니다</div>
  </div>
<?php else: ?>
  <?php foreach ($filtered as $v):
    $genre = $v['genre'];
    $color = $genre_colors[$genre] ?? '#888';
    $icon  = $genre_icons[$genre] ?? '';
    $lang  = $v['lang'];
    $date  = date('Y-m-d H:i', strtotime($v['created_at']));
    $size  = number_format($v['file_size_mb'], 1);
    $video_url = '/videos/videos/' . htmlspecialchars($v['filename']);
  ?>
  <div class="card">
    <video class="card-video" controls preload="none" playsinline>
      <source src="<?= $video_url ?>" type="video/mp4">
    </video>
    <div class="card-body">
      <div class="card-meta">
        <span class="badge badge-genre" style="background:<?= $color ?>"><?= $icon ?> <?= $genre ?></span>
        <span class="badge badge-lang"><?= lang_label($lang) ?></span>
      </div>
      <div class="card-title"><?= htmlspecialchars($v['title']) ?></div>
      <div class="card-info">
        <span><?= $date ?></span>
        <span><?= $size ?> MB</span>
      </div>
    </div>
  </div>
  <?php endforeach; ?>
<?php endif; ?>
</div>

</body>
</html>
