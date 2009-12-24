require 'spec_helpers.rb'

describe 'IMG VQVZ' do
  it 'should respond to /' do
    get '/'
    last_response.should be_ok
    last_response.body.should match(/page - 1/)
  end

  it 'should respond to /page/n' do
    get '/page/2'
    last_response.should be_ok
    last_response.body.should match(/page - 2/)
  end

  it 'should respond to /about' do
    get '/about'
    last_response.should be_ok
    last_response.body.should match(/<h2>About<\/h2>/)
  end

  it 'should respond to /news' do
    get '/news'
    last_response.should be_ok
    last_response.body.should match(/<h2>News<\/h2>/)
  end

  it 'should respond to /sets' do
    get '/sets'
    last_response.should be_ok
    last_response.body.should match(/<h2>Sets<\/h2>/)
  end

  it 'should respond to /set/id' do
    get '/set/72157608508468675'
    last_response.should be_ok
    last_response.body.should match(/tag - 72157608508468675 | page - 0/)
  end

  it 'should respond to /set/tag_name' do
    get '/set/shima'
    last_response.should be_ok
    last_response.body.should match(/tag - vqvz:set=shima | page - 0/)
  end

  it 'should respond to /set/set_name' do
    get '/set/blansdowne'
    last_response.should be_ok
    last_response.body.should match(/tag - 72157619603386788 | page - 0/)
  end

  it 'should respond to /photo/id' do
    # photo of shima on Flickr
    get '/photo/4196874052'
    last_response.should be_ok
    last_response.body.should match('<h2>Shima<\/h2>')    
  end

  it 'should return a 404 on an error' do
    get '/404'
    last_response.status.should == 404
  end

  # assumes we have at least 2 pages worth of photos
  it 'should let you move forward and back via page links' do
    visit '/'
    last_response.should be_ok
    click_link 'Next'
    last_response.should be_ok
    last_request.url.should == 'http://example.org/page/2'
    click_link 'Next'
    last_response.should be_ok
    last_request.url.should == 'http://example.org/page/3'
    click_link 'Prev'
    last_response.should be_ok
    last_request.url.should == 'http://example.org/page/2'
    click_link 'Prev'
    last_response.should be_ok
    last_request.url.should == 'http://example.org/'
  end
end
