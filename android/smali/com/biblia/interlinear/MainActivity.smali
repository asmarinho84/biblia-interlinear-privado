.class public Lcom/biblia/interlinear/MainActivity;
.super Landroid/app/Activity;
.source "MainActivity.java"

# Tela única: WebView que carrega o app web embutido em assets/app (100% offline).

.field private web:Landroid/webkit/WebView;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V
    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .locals 3
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    # mantém a tela ligada (sem apagar nem ir para a tela de bloqueio) enquanto o app está aberto
    invoke-virtual {p0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;
    move-result-object v0
    const/16 v1, 0x80
    invoke-virtual {v0, v1}, Landroid/view/Window;->addFlags(I)V

    new-instance v0, Landroid/webkit/WebView;
    invoke-direct {v0, p0}, Landroid/webkit/WebView;-><init>(Landroid/content/Context;)V
    iput-object v0, p0, Lcom/biblia/interlinear/MainActivity;->web:Landroid/webkit/WebView;

    # fundo igual ao da tela de abertura (sem piscar em branco ao carregar)
    const v1, -0x85c4e4
    invoke-virtual {v0, v1}, Landroid/webkit/WebView;->setBackgroundColor(I)V
    const/4 v1, 0x1
    invoke-virtual {v0, v1}, Landroid/view/View;->setKeepScreenOn(Z)V

    invoke-virtual {v0}, Landroid/webkit/WebView;->getSettings()Landroid/webkit/WebSettings;
    move-result-object v1
    const/4 v2, 0x1
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V
    invoke-virtual {v1, v2}, Landroid/webkit/WebSettings;->setDomStorageEnabled(Z)V

    new-instance v2, Landroid/webkit/WebViewClient;
    invoke-direct {v2}, Landroid/webkit/WebViewClient;-><init>()V
    invoke-virtual {v0, v2}, Landroid/webkit/WebView;->setWebViewClient(Landroid/webkit/WebViewClient;)V

    invoke-virtual {p0, v0}, Lcom/biblia/interlinear/MainActivity;->setContentView(Landroid/view/View;)V

    const-string v1, "file:///android_asset/app/index.html"
    invoke-virtual {v0, v1}, Landroid/webkit/WebView;->loadUrl(Ljava/lang/String;)V
    return-void
.end method

.method public onBackPressed()V
    .locals 2
    iget-object v0, p0, Lcom/biblia/interlinear/MainActivity;->web:Landroid/webkit/WebView;
    invoke-virtual {v0}, Landroid/webkit/WebView;->canGoBack()Z
    move-result v1
    if-eqz v1, :sair
    invoke-virtual {v0}, Landroid/webkit/WebView;->goBack()V
    return-void
    :sair
    invoke-super {p0}, Landroid/app/Activity;->onBackPressed()V
    return-void
.end method
