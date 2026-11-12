import pytest

BOOKS_HTML = """
<html><body><section><ol class="row">
<li><article class="product_pod">
  <p class="star-rating Three"></p>
  <h3><a href="a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a></h3>
  <div class="product_price"><p class="price_color">£51.77</p>
  <p class="instock availability"><i class="icon-ok"></i> In stock</p></div>
</article></li>
<li><article class="product_pod">
  <p class="star-rating One"></p>
  <h3><a href="tipping-the-velvet_999/index.html" title="Tipping the Velvet">Tipping the ...</a></h3>
  <div class="product_price"><p class="price_color">Â£53.74</p>
  <p class="availability">Out of stock</p></div>
</article></li>
</ol>
<ul class="pager"><li class="next"><a href="page-2.html">next</a></li></ul>
</section></body></html>
"""

QUOTES_HTML = """
<html><body>
<div class="quote"><span class="text">“The world as we have created it is a process of our thinking.”</span>
  <span>by <small class="author">Albert Einstein</small></span>
  <div class="tags">Tags: <a class="tag" href="/tag/change/">change</a><a class="tag" href="/tag/thinking/">thinking</a></div>
</div>
<div class="quote"><span class="text">“A day without sunshine is like, you know, night.”</span>
  <span>by <small class="author">Steve Martin</small></span>
  <div class="tags">Tags: </div>
</div>
<nav><ul class="pager"><li class="next"><a href="/js/page/2/">Next</a></li></ul></nav>
</body></html>
"""


@pytest.fixture
def books_html():
    return BOOKS_HTML


@pytest.fixture
def quotes_html():
    return QUOTES_HTML
