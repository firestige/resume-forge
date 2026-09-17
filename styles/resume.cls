\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{resume}[2026/03/06 My Resume class, based on billryan/resume]
\LoadClass[11pt]{article}

% ── 基础包 ──────────────────────────────────────────────────────────────────
\setlength{\parindent}{0pt}
\RequirePackage{xltxtra}
\RequirePackage{xifthen}
\RequirePackage{hyperref}
\hypersetup{hidelinks}
\RequirePackage{url}
\urlstyle{tt}
\RequirePackage{fontawesome5}
\RequirePackage{fontspec}
\RequirePackage{xeCJK}

% ── 字体配置 ─────────────────────────────────────────────────────────────────
% 英文主字体：系统自带，CI 上使用 Latin Modern
\setmainfont{TeX Gyre Termes}[
  UprightFont    = *,
  BoldFont       = * Bold,
  ItalicFont     = * Italic,
  BoldItalicFont = * Bold Italic,
]

% 中文字体：macOS 使用 Songti SC，Linux CI 使用 Noto Serif CJK SC
\IfFontExistsTF{Songti SC}{
  \setCJKmainfont{Songti SC}[BoldFont={Songti SC Bold}]
  \setCJKsansfont{PingFang SC}[BoldFont={PingFang SC Semibold}]
}{
  \setCJKmainfont{Noto Serif CJK SC}[BoldFont={Noto Serif CJK SC Bold}]
  \setCJKsansfont{Noto Sans CJK SC}[BoldFont={Noto Sans CJK SC Bold}]
}

% ── 页面布局 ─────────────────────────────────────────────────────────────────
\RequirePackage[
  a4paper,
  left=0.75in,
  right=0.75in,
  top=0.65in,
  bottom=0.55in,
  nohead
]{geometry}

% ── 列表间距 ─────────────────────────────────────────────────────────────────
\RequirePackage{enumitem}
\setlist{noitemsep}
\setlist[itemize]{topsep=0.25em, leftmargin=1.5pc}

% ── 行距 ─────────────────────────────────────────────────────────────────────
\RequirePackage{setspace}

% ── Section 样式 ─────────────────────────────────────────────────────────────
\RequirePackage{titlesec}

\titleformat{\section}
  {\Large\scshape\raggedright}
  {}{0em}{}
  [\titlerule]
\titlespacing*{\section}{0cm}{0.5\baselineskip}{*1.8}

\titleformat{\subsection}
  {\large\raggedright}
  {}{0em}{}
\titlespacing*{\subsection}{0cm}{*1.6}{*0.5}

% ── 自定义命令 ────────────────────────────────────────────────────────────────

% 日期+标题子节
\newcommand{\datedsubsection}[2]{%
  \subsection[#1]{#1 \hfill #2}%
}

% 角色/技术栈标注
\newcommand{\role}[2]{%
  {\par\textit{#1} \ifthenelse{\isempty{#2}}{}{~\textbullet~#2}\par}%
  \vspace{0.75ex}%
}

% 姓名（居中大字）
\newcommand{\name}[1]{%
  \centerline{\huge\bfseries{#1}}%
  \vspace{1.25ex}%
}

% 基本信息栏
\newcommand{\basicInfo}[1]{%
  \centerline{\sffamily\normalsize{#1}}%
  \vspace{1.5ex}%
}

% 联系方式快捷命令
\newcommand{\emaillink}[1]{\faEnvelope\ \href{mailto:#1}{#1}}
\newcommand{\phone}[1]{\faPhone\ {#1}}
\newcommand{\github}[2][]{\faGithub\ \ifthenelse{\isempty{#1}}{\href{#2}{#2}}{\href{#2}{#1}}}
\newcommand{\homepage}[2][]{\faLink\ \ifthenelse{\isempty{#1}}{\href{#2}{#2}}{\href{#2}{#1}}}
