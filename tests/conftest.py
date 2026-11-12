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


DETAIL_HTML = """
<html><body>
<ul class="breadcrumb">
  <li><a href="../../index.html">Home</a></li>
  <li><a href="../category/books_1/index.html">Books</a></li>
  <li><a href="../category/books/poetry_23/index.html">Poetry</a></li>
  <li class="active">A Light in the Attic</li>
</ul>
<div class="col-sm-6 product_main">
  <h1>A Light in the Attic</h1>
  <p class="price_color">£51.77</p>
  <p class="instock availability"><i class="icon-ok"></i> In stock (22 available)</p>
</div>
<table class="table table-striped">
  <tr><th>UPC</th><td>a897fe39b1053632</td></tr>
  <tr><th>Product Type</th><td>Books</td></tr>
  <tr><th>Price (excl. tax)</th><td>£51.77</td></tr>
  <tr><th>Availability</th><td>In stock (22 available)</td></tr>
  <tr><th>Number of reviews</th><td>0</td></tr>
</table>
</body></html>
"""


@pytest.fixture
def detail_html():
    return DETAIL_HTML
