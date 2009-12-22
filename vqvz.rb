require 'sinatra'
require 'flickraw'
require 'erubis'

# Some basic information about an image (on Flickr)
class Image
  attr_accessor :id, :img_url, :flickr_url, :title, :date
  
  def initialize(id, img_url,title, date)
    @id, @img_url, @title, @date = id, img_url, title, date
    @flickr_url = "http://flickr.com/photos/#{CONF[:user]}/#{id}"
  end
end

# basic information about a set
class FlickrSet
  attr_accessor :id, :title, :thumbnail, :slug
  
  def slug
    @slug ||= @title.downcase.gsub(/[^a-z0-9_]/, '-')
  end
  
  def initialize(id, title, thumbnail, slug = nil)
    @id, @title, @thumbnail, @slug = id, title, thumbnail, slug
  end
end

# Sinatra !!

configure do
  CONF = YAML::load_file("conf.yml")
  CONF[:user_id] = flickr.people.findByUsername(:username => CONF[:user]).id
  user = flickr.people.getInfo(:user_id => CONF[:user_id])
  CONF[:flickr_profile] = user.profileurl
  CONF[:name] = user.realname
  SETS = YAML::load_file("sets.yml")
  SET_IDS = SETS.map { |name, set| set[:set_id] }
end

before do
  expires 86400, :public, :must_revalidate
  @config = CONF
end

helpers do
  # Loads 10 images from Flickr, offset by however many pages.
  # If :tag is specified in the conf file, we filter by that
  # machine tag. if tag is supplied as a parameter, we will
  # filter by that instead.
  def load_images(page, tag=nil)
    @page = page.to_i
    @tag = tag
    params = { :user_id => CONF[:user_id], :extras => 'date_taken' }
    params[:machine_tags] = CONF[:tag] unless CONF[:tag].nil?
    params[:machine_tags] = tag unless tag.nil?
    params[:per_page] = 10 unless page == 0
    params[:page] = page unless page == 0
    photos = flickr.photos.search(params)
    @pages = photos.pages
    @sequence = build_sequence(photos)
  end

  # load all the photos in the given flickr set.
  def load_set(id)
    @page = 0
    @tag = id
    params = { :user_id => CONF[:user_id], :extras => 'date_taken', :photoset_id => id }
    set_info = flickr.photosets.getPhotos(params)
    @sequence = build_sequence(set_info.photo)
  end

  # build list of images.
  def build_sequence(photos)
    return [] if photos.nil?
    photos.map do |photo|
      sizes = flickr.photos.getSizes(:photo_id => photo.id)
      size = sizes.find { |s| s.label == 'Large' }
      size ||= sizes.find { |s| s.label == 'Medium'}
      Image.new(photo.id, size.source, photo.title, photo.datetaken[0..9])
    end
  end
end

# loads the most recent photos from Flickr
get '/' do
  load_images(1)
  @show_nav = true
  erubis :index
end

# loads the most recent photos from Flickr, offset by however many pages.
get '/page/:num' do |page|
  load_images(page)
  @show_nav = true
  erubis :index
end

get '/sets' do
  @sets = SETS.map do |slug, set|
    FlickrSet.new(set[:set_id], set[:title], set[:thumbnail], slug)
  end
  erubis :sets
end

get %r{/set/(\d+)} do |id|
  load_set(id)
  erubis :index
end

get '/set/:name' do |name|
  SETS[name].nil? ? load_images(0, "vqvz:set=#{name}") : load_set(SETS[name][:set_id])
  erubis :index
end

get '/about/?' do
  erubis :about
end

get '/news/?' do
  erubis :news
end

# load image from Flickr
get %r{/photo/(\d+)} do |id|
  info = flickr.photos.getInfo(:photo_id =>id)
  sizes = flickr.photos.getSizes(:photo_id => id)
  size = sizes.find { |s| s.label == 'Large' }
  size ||= sizes.find { |s| s.label == 'Medium'}
  @photo = Image.new(id, size.source, info.title, info.dates.taken[0..9])
  erubis :photo
end

# Error Handlers in Production

configure :production do
  not_found do
    erubis :error
  end

  error do
    erubis :error
  end
end
