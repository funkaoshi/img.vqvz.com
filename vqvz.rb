require 'sinatra'
require 'erubis'
require 'flickraw/lib/flickraw.rb'

configure do
  CONF = YAML::load_file("conf.yml")
  CONF[:user_id] = flickr.people.findByUsername(:username => CONF[:user]).id
  user = flickr.people.getInfo(:user_id => CONF[:user_id])
  CONF[:total_pages] = user.photos.count.to_i / 10 + 1
  CONF[:flickr_profile] = user.profileurl
  CONF[:name] = user.realname
end

before do
  @config = CONF
end

class Image
  attr_accessor :id, :img_url, :flickr_url, :title, :date
  def initialize(id, img_url,title, date)
    @id = id
    @img_url = img_url
    @flickr_url = "http://flickr.com/photos/#{CONF[:user]}/#{id}"
    @title = title
    @date = date
  end
end

helpers do
  def load_images(page)
    params = {  :per_page => 10, :page => page, :user_id => CONF[:user_id] }
    params[:machine_tags] = CONF[:tag] unless CONF[:tag].nil?
    photos = flickr.photos.search(params)
    @sequence = []
    photos.each do |photo| 
      info = flickr.photos.getInfo(:photo_id => photo.id, :secret => photo.secret)
      @sequence << Image.new(info.id, FlickRaw.url_b(info), info.title, info.dates.taken[0..9])
    end
  end
end
    

get '/' do
  load_images(1)
  @num = 1
  erb :index
end

get '/page-:num' do |num|
  load_images(num)
  @num = num.to_i
  erb :index
end

error do
  'Sorry there was a nasty error - ' + request.env['sinatra.error'].name
end
