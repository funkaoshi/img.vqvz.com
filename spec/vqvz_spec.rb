require 'spec_helpers.rb'

describe "IMG VQVZ" do
  include Rack::Test::Methods

  def app
    @app ||= Sinatra::Application
  end

  it "should respond to /" do
    get '/'
    last_response.should be_ok
    
  end

  it "should respond to /about" do
    get '/about'
    last_response.should be_ok
    last_response.body.should match(/<h2>About<\/h2>/)
  end

  it "should respond to /news" do
    get '/news'
    last_response.should be_ok
    last_response.body.should match(/<h2>News<\/h2>/)
  end

  it "should respond to /sets" do
    get '/sets'
    last_response.should be_ok
    last_response.body.should match(/<h2>Sets<\/h2>/)
  end

  it "should respond to /photo/id" do
    # photo of shima on Flickr
    get '/photo/4196874052/'
    last_response.should be_ok
    last_response.body.should match(/tag - 4196874052/)
  end

  it "should respond to /set/id" do
    get '/set/72157608508468675'
    last_response.should be_ok
    last_response.body.should match(/tag - 72157608508468675/)
  end

  it "should respond to /set/tag_name" do
    get '/set/shima'
    last_response.should be_ok
    last_response.body.should match(/tag - vqvz:set=shima/)
  end

  it 'should respond to /set/set_name' do
    get '/set/blansdowne'
    last_response.should be_ok
    last_response.body.should match(/tag - 72157619603386788/)
  end

  it "should return a 404 on an error" do
    get '/404'
    last_response.status.should == 404
  end
end
